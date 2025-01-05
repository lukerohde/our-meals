import json
import pulumi
import pulumi_aws as aws

# Pulumi configuration
config = pulumi.Config()
stack = pulumi.get_stack()

# Get configuration
BUCKET_NAME = config.require('mediaBucketName')
ALLOWED_ORIGINS = config.require('allowedOrigins').split(',')

def create_s3_bucket_with_cors(bucket_name: str, environment: str):
    # Create the bucket with encryption and versioning
    bucket = aws.s3.Bucket(bucket_name,
        acl='private',
        server_side_encryption_configuration=aws.s3.BucketServerSideEncryptionConfigurationArgs(
            rule=aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
                apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm="AES256"
                )
            )
        ),
        tags={
            'Environment': environment,
            'Name': f'MediaBucket-{environment}',
            'ManagedBy': 'pulumi'
        }
    )

    # Set up CORS
    cors = aws.s3.BucketCorsConfigurationV2(f'{bucket_name}-cors',
        bucket=bucket.id,
        cors_rules=[aws.s3.BucketCorsConfigurationV2CorsRuleArgs(
            allowed_methods=['GET', 'POST', 'PUT', 'DELETE'],
            allowed_origins=ALLOWED_ORIGINS,
            allowed_headers=['*'],
            expose_headers=['ETag'],
            max_age_seconds=3000,
        )],
    )

    # Block public access (we'll use a bucket policy instead)
    public_access_block = aws.s3.BucketPublicAccessBlock(f'{bucket_name}-public-access-block',
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=False,  # We need this false to allow our policy
        ignore_public_acls=True,
        restrict_public_buckets=False  # We need this false to allow our policy
    )

    # Add bucket policy for public read access through CloudFront/signed URLs
    policy = aws.s3.BucketPolicy(f'{bucket_name}-policy',
        bucket=bucket.id,
        policy=bucket.arn.apply(
            lambda arn: json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    # Allow Django to read/write objects
                    {
                        "Sid": "AllowDjangoAccess",
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": "*"  # You'll want to restrict this to your Django app's IAM role
                        },
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject"
                        ],
                        "Resource": f"{arn}/*"
                    },
                    # Allow public read access only if request comes from allowed origins
                    {
                        "Sid": "AllowPublicRead",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"{arn}/*",
                        "Condition": {
                            "StringLike": {
                                "aws:Referer": ALLOWED_ORIGINS
                            }
                        }
                    }
                ]
            })
        )
    )

    return bucket

# Create S3 bucket
media_bucket = create_s3_bucket_with_cors(BUCKET_NAME, stack)

# Export the bucket name and ARN
pulumi.export('bucket_name', media_bucket.id)
pulumi.export('bucket_arn', media_bucket.arn)