# Our Meals Pulumi Infrastructure

This directory contains the Pulumi configuration for Our Meals S3 infrastructure.

## Features

- Environment-specific S3 buckets for recipe photos
- CORS configuration for web access
- Secure bucket policies with Referer-based access control
- Server-side encryption
- Lifecycle rules for incomplete uploads
- Public access blocking

## Required Setup

1. **AWS Account**:
   - Create AWS account
   - Create IAM user with these permissions (IAM, create policy, create user, attach policy):
     ```json
     {
         "Version": "2012-10-17",
         "Statement": [
             {
                 "Effect": "Allow",
                 "Action": [
                     "s3:*"
                 ],
                 "Resource": "*"
             }
         ]
     }
     ```
   - Get access key and secret

2. **Pulumi Account** (recommended for CI):
   - Sign up at app.pulumi.com (free)
   - Get access token from Account Settings
   - Or use local state for development

## Quick Start

1. Copy environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```bash
# AWS credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Pulumi configuration (choose one)
# 1. Pulumi Service (recommended for CI)
PULUMI_ACCESS_TOKEN=your_token

# 2. Local State (development only)
# PULUMI_CONFIG_PASSPHRASE=your_passphrase

# Stack settings
PULUMI_STACK=dev
```

3. Edit `Pulumi.dev.yaml` and `Pulumi.prod.yaml` with your bucket name:

4. Deploy using Docker Compose:
```bash
# Preview changes
docker-compose run --rm pulumi preview

# Apply changes
docker-compose run --rm pulumi up --yes
```

## State Management

For CI environments:
- Pulumi Service is **recommended**
  - Free hosted state management
  - Built-in state locking
  - No infrastructure needed
  - Set `PULUMI_ACCESS_TOKEN` in CI

Alternative options:
1. **Local State** (development only):
   - Set `PULUMI_CONFIG_PASSPHRASE`
   - State stored in `.pulumi`
   - Not suitable for CI

2. **Custom Backend**:
   - Use S3 for state storage:
     ```bash
     cd ../boto
     docker-compose run setup_s3 --bucket pulumi-state
     cd ../pulumi
     ```
   - Set `PULUMI_BACKEND_URL=s3://your-bucket-name/pulumi/state`

## CI/CD Usage

```yaml
pulumi_deploy:
  image: ${CI_REGISTRY_IMAGE}/pulumi:latest
  script:
    - ./scripts/entrypoint.sh up --yes
  variables:
    AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
    AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
    AWS_REGION: ${AWS_REGION}
    # Required for CI (choose one)
    PULUMI_ACCESS_TOKEN: ${PULUMI_ACCESS_TOKEN}
    # PULUMI_BACKEND_URL: ${PULUMI_BACKEND_URL}
    PULUMI_STACK: ${ENVIRONMENT}
```

## Cleanup

Remove all resources:
```bash
docker-compose run pulumi destroy
```

## Comparison with Other Approaches

### Advantages
- Use real programming languages (Python, TypeScript, etc.)
- Free hosted state management
- Rich type system and IDE support
- Easy to write complex logic and tests
- Works with any cloud provider
- Strong policy and RBAC support

### Disadvantages
- Smaller community than Terraform
- Requires Pulumi account for best experience
- More complex than CDK for AWS-only workloads
- Learning curve for infrastructure concepts
- Can write non-idempotent code if not careful
