#!/bin/bash

# Utility functions for DeepSeek Bedrock deployment

# Check if AWS CLI is configured
check_aws_config() {
    if ! command -v aws &> /dev/null; then
        echo "AWS CLI is not installed"
        return 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        echo "AWS credentials not configured"
        return 1
    fi
    
    return 0
}

# Deploy CloudFormation stack
deploy_stack() {
    local stack_name=$1
    local template_file=$2
    local profile=${3:-default}
    
    aws cloudformation deploy \
        --template-file "$template_file" \
        --stack-name "$stack_name" \
        --capabilities CAPABILITY_IAM \
        --profile "$profile"
}

# Check stack status
check_stack_status() {
    local stack_name=$1
    local profile=${2:-default}
    
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query 'Stacks[0].StackStatus' \
        --output text \
        --profile "$profile"
}

# Get stack outputs
get_stack_outputs() {
    local stack_name=$1
    local profile=${2:-default}
    
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --query 'Stacks[0].Outputs' \
        --output json \
        --profile "$profile"
}

# Wait for stack operation to complete
wait_for_stack() {
    local stack_name=$1
    local profile=${2:-default}
    
    aws cloudformation wait stack-create-complete \
        --stack-name "$stack_name" \
        --profile "$profile"
}

# Delete stack
delete_stack() {
    local stack_name=$1
    local profile=${2:-default}
    
    aws cloudformation delete-stack \
        --stack-name "$stack_name" \
        --profile "$profile"
}

# Main deployment function
deploy_deepseek() {
    local stack_name=${1:-deepseek-bedrock-stack}
    local profile=${2:-default}
    
    echo "Deploying DeepSeek Bedrock stack..."
    deploy_stack "$stack_name" "deepseek-bedrock-stack.yaml" "$profile"
    
    echo "Waiting for deployment to complete..."
    wait_for_stack "$stack_name" "$profile"
    
    echo "Deployment complete. Stack outputs:"
    get_stack_outputs "$stack_name" "$profile"
} 