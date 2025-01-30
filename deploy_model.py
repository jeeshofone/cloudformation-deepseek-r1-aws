#!/usr/bin/env python3
"""
DeepSeek Bedrock Model Deployment Script
This script deploys the DeepSeek model to AWS Bedrock using CloudFormation
"""

import boto3
import argparse
import time
import sys
import json
from botocore.exceptions import ClientError
from huggingface_hub import snapshot_download

def deploy_stack(stack_name, template_file, profile_name=None, region='us-west-2'):
    """
    Deploy CloudFormation stack for DeepSeek model
    
    Args:
        stack_name (str): Name of the CloudFormation stack
        template_file (str): Path to CloudFormation template
        profile_name (str): AWS profile name to use
        region (str): AWS region to deploy to
    """
    session = boto3.Session(profile_name=profile_name, region_name=region)
    cf = session.client('cloudformation')
    
    try:
        # Read template
        with open(template_file, 'r') as f:
            template_body = f.read()
        
        # Deploy stack
        print(f"Deploying stack {stack_name}...")
        cf.create_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Capabilities=['CAPABILITY_IAM']
        )
        
        # Wait for completion
        print("Waiting for stack creation to complete...")
        waiter = cf.get_waiter('stack_create_complete')
        waiter.wait(
            StackName=stack_name,
            WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
        )
        
        # Get outputs
        response = cf.describe_stacks(StackName=stack_name)
        outputs = {
            output['OutputKey']: output['OutputValue'] 
            for output in response['Stacks'][0]['Outputs']
        }
        
        print("\nStack deployment complete!")
        print("\nStack Outputs:")
        print(json.dumps(outputs, indent=2))
        
        return outputs
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'AlreadyExistsException':
            print(f"Stack {stack_name} already exists. Updating...")
            try:
                cf.update_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Capabilities=['CAPABILITY_IAM']
                )
                waiter = cf.get_waiter('stack_update_complete')
                waiter.wait(
                    StackName=stack_name,
                    WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
                )
                print("Stack update complete!")
            except ClientError as update_error:
                if 'No updates are to be performed' in str(update_error):
                    print("No updates needed for the stack.")
                else:
                    raise update_error
        else:
            raise e

def deploy_model():
    # Initialize clients
    cf = boto3.client('cloudformation', region_name='us-west-2')
    s3 = boto3.client('s3', region_name='us-west-2')

    # Deploy CloudFormation stack
    with open('deepseek-bedrock-stack.yaml', 'r') as f:
        template_body = f.read()

    stack_name = 'deepseek-bedrock-stack'
    
    print("Deploying CloudFormation stack...")
    cf.create_stack(
        StackName=stack_name,
        TemplateBody=template_body,
        Capabilities=['CAPABILITY_IAM']
    )

    # Wait for stack creation to complete
    waiter = cf.get_waiter('stack_create_complete')
    waiter.wait(StackName=stack_name)

    # Get stack outputs
    response = cf.describe_stacks(StackName=stack_name)
    outputs = {
        output['OutputKey']: output['OutputValue'] 
        for output in response['Stacks'][0]['Outputs']
    }

    # Download model from HuggingFace
    print("Downloading model from HuggingFace...")
    local_dir = "DeepSeek-R1-Distill-Llama-8B"
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
    snapshot_download(
        repo_id="deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        local_dir=local_dir
    )

    # Upload model to S3
    print("Uploading model to S3...")
    bucket_name = outputs['ModelStorageBucketName']
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            s3_key = os.path.join(
                'DeepSeek-R1-Distill-Llama-8B',
                os.path.relpath(local_path, local_dir)
            )
            s3.upload_file(local_path, bucket_name, s3_key)

    print("Deployment complete!")
    print(f"Model import job ARN: {outputs['ModelImportJobArn']}")

def main():
    parser = argparse.ArgumentParser(description='Deploy DeepSeek model to AWS Bedrock')
    parser.add_argument('--stack-name', default='deepseek-bedrock-stack',
                      help='Name of the CloudFormation stack')
    parser.add_argument('--template', default='deepseek-bedrock-stack.yaml',
                      help='Path to CloudFormation template')
    parser.add_argument('--profile', help='AWS profile name to use')
    parser.add_argument('--region', default='us-west-2',
                      help='AWS region to deploy to')
    
    args = parser.parse_args()
    
    try:
        deploy_stack(
            args.stack_name,
            args.template,
            args.profile,
            args.region
        )
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 