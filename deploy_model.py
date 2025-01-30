#!/usr/bin/env python3
"""
DeepSeek Bedrock Model Deployment Script
This script handles CloudFormation stack deployment for the DeepSeek Bedrock model
"""

import os
import boto3
import argparse
import tempfile
import subprocess
import shutil
from pathlib import Path
from botocore.exceptions import ClientError

def create_deployment_package():
    """Create Lambda deployment package with all required dependencies"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create requirements.txt
        requirements = '''
        transformers
        huggingface-hub[hf_transfer]
        boto3
        cfnresponse
        '''.strip()
        
        req_file = Path(tmp_dir) / 'requirements.txt'
        req_file.write_text(requirements)
        
        # Install dependencies
        subprocess.check_call([
            'pip', 'install',
            '-r', str(req_file),
            '--target', tmp_dir
        ])
        
        # Write Lambda handler code
        handler_code = '''
import os
import json
import boto3
import cfnresponse
from transformers import AutoTokenizer
from huggingface_hub import snapshot_download
from botocore.config import Config

def handler(event, context):
    try:
        if event['RequestType'] in ['Create', 'Update']:
            os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
            local_dir = "/tmp/model"
            snapshot_download(
                repo_id="deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
                local_dir=local_dir
            )
            
            s3 = boto3.client('s3')
            bucket = event['ResourceProperties']['BucketName']
            prefix = event['ResourceProperties']['S3Prefix']
            
            for root, dirs, files in os.walk(local_dir):
                for file in files:
                    local_path = os.path.join(root, file)
                    s3_key = os.path.join(
                        prefix,
                        os.path.relpath(local_path, local_dir)
                    )
                    s3.upload_file(local_path, bucket, s3_key)
            
            bedrock = boto3.client('bedrock')
            response = bedrock.create_model_customization_job(
                jobName=event['ResourceProperties']['JobName'],
                importedModelName=event['ResourceProperties']['ImportedModelName'],
                roleArn=event['ResourceProperties']['RoleArn'],
                modelDataSource={
                    's3DataSource': {
                        's3Uri': f"s3://{bucket}/{prefix}/"
                    }
                }
            )
            
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'JobArn': response['jobArn']
            })
        else:
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {
            'Error': str(e)
        })
        '''.strip()
        
        handler_file = Path(tmp_dir) / 'model_deployment.py'
        handler_file.write_text(handler_code)
        
        # Create zip file
        shutil.make_archive('deployment_package', 'zip', tmp_dir)
        return Path('deployment_package.zip')

def create_or_update_stack(stack_name, region):
    """Create or update CloudFormation stack"""
    # First create and upload Lambda package
    package_path = create_deployment_package()
    
    # Initialize AWS clients
    s3 = boto3.client('s3', region_name=region)
    cfn = boto3.client('cloudformation', region_name=region)
    
    # Get template from file
    with open('deepseek-bedrock-stack.yaml', 'r') as f:
        template_body = f.read()
    
    try:
        # Create stack first to get the bucket name
        print(f"Creating initial stack for S3 bucket...")
        try:
            response = cfn.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=['CAPABILITY_IAM']
            )
            waiter = cfn.get_waiter('stack_create_complete')
        except cfn.exceptions.AlreadyExistsException:
            print(f"Stack {stack_name} exists, getting bucket name...")
            response = cfn.describe_stacks(StackName=stack_name)
            for output in response['Stacks'][0]['Outputs']:
                if output['OutputKey'] == 'ModelStorageBucketName':
                    bucket_name = output['OutputValue']
                    break
        else:
            # Wait for bucket creation
            print("Waiting for S3 bucket creation...")
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={'Delay': 5, 'MaxAttempts': 60}
            )
            # Get bucket name from outputs
            response = cfn.describe_stacks(StackName=stack_name)
            for output in response['Stacks'][0]['Outputs']:
                if output['OutputKey'] == 'ModelStorageBucketName':
                    bucket_name = output['OutputValue']
                    break
        
        # Upload Lambda package to S3
        print(f"Uploading Lambda package to S3 bucket {bucket_name}...")
        s3.upload_file(
            str(package_path),
            bucket_name,
            'lambda/model_deployment.zip'
        )
        
        # Update stack with Lambda function
        print(f"Updating stack {stack_name} with Lambda function...")
        try:
            cfn.update_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=['CAPABILITY_IAM']
            )
            waiter = cfn.get_waiter('stack_update_complete')
            print("Waiting for stack update to complete...")
            waiter.wait(
                StackName=stack_name,
                WaiterConfig={'Delay': 5, 'MaxAttempts': 60}
            )
            print("Stack deployment completed successfully!")
        except cfn.exceptions.ClientError as e:
            if 'No updates are to be performed' in str(e):
                print("No updates needed for the stack.")
            else:
                raise
        
    except Exception as e:
        print(f"Error deploying stack: {str(e)}")
        raise
    finally:
        # Cleanup
        package_path.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description='Deploy DeepSeek model to AWS Bedrock')
    parser.add_argument('--stack-name', required=True, help='Name of the CloudFormation stack')
    parser.add_argument('--region', required=True, help='AWS region to deploy to')
    
    args = parser.parse_args()
    create_or_update_stack(args.stack_name, args.region)

if __name__ == '__main__':
    main() 