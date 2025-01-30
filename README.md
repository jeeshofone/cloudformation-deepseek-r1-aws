# DeepSeek Bedrock Model Deployment

This project provides an automated deployment solution for importing DeepSeek's distilled Llama models to Amazon Bedrock using AWS native services. The deployment is handled entirely through AWS services, eliminating the need for local compute resources.

## Features

- Serverless deployment using AWS Lambda and CloudFormation
- Support for both DeepSeek-R1-Distill-Llama-8B and 70B models
- AWS profile support for multi-account deployment
- Automated model download and import process
- Secure S3 bucket configuration for model storage
- IAM roles with least privilege access

## Prerequisites

- AWS CLI installed and configured
- Appropriate AWS permissions to create:
  - IAM roles
  - S3 buckets
  - Lambda functions
  - Bedrock model imports
- Access to Amazon Bedrock service

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cloudformation-deepseek-r1-aws.git
cd cloudformation-deepseek-r1-aws
```

2. (Optional) Create a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install boto3 botocore
```

## Usage

### Basic Deployment

Deploy using default settings:

```bash
python deploy_model.py
```

### Advanced Deployment Options

Deploy with custom settings:

```bash
python deploy_model.py \
  --stack-name my-deepseek-stack \
  --profile my-aws-profile \
  --region us-west-2
```

### Command Line Arguments

- `--stack-name`: Name of the CloudFormation stack (default: deepseek-bedrock-stack)
- `--template`: Path to CloudFormation template (default: deepseek-bedrock-stack.yaml)
- `--profile`: AWS profile name to use (optional)
- `--region`: AWS region to deploy to (default: us-west-2)

## Architecture

The deployment process follows these steps:

1. CloudFormation stack creation begins
2. S3 bucket is created for model storage
3. Lambda function is created with necessary IAM roles
4. Lambda function:
   - Downloads model from HuggingFace
   - Uploads to S3 bucket
   - Initiates Bedrock model import
5. Stack outputs provide necessary ARNs and resource information

## Security

- S3 bucket is configured with:
  - Server-side encryption
  - Public access blocking
  - Versioning enabled
- IAM roles follow least privilege principle
- No credentials stored in code
- AWS profile support for secure authentication

## Troubleshooting

Common issues and solutions:

1. Stack creation fails:
   - Check CloudWatch logs for Lambda function errors
   - Verify AWS permissions
   - Ensure sufficient Lambda timeout and memory

2. Model import fails:
   - Verify S3 bucket permissions
   - Check Bedrock service quotas
   - Ensure model files are correctly uploaded

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- DeepSeek AI for the model
- AWS for Bedrock service
- HuggingFace for model hosting 