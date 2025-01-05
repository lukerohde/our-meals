"""Test S3 infrastructure configuration"""

import pytest
from pulumi import Config, automation as auto

def test_s3_config():
    """Test S3 configuration"""
    config = Config()
    
    # Test environment is required
    with pytest.raises(Exception):
        config.require('non_existent')
    
    # Test allowed origins default
    assert config.get_object('allowed_origins') == ["https://our-meals.com"]

def test_s3_stack():
    """Test S3 stack configuration"""
    work = auto.LocalWorkspace()
    stack = auto.select_stack(stack_name="dev", work_dir=".")
    
    # Test stack configuration
    config = stack.get_config()
    assert "environment" in config
    assert config["environment"]["value"] == "dev"
    
    # Test stack outputs
    outputs = stack.outputs()
    assert "bucket_name" in outputs
    assert "bucket_arn" in outputs
    assert outputs["bucket_name"].value.startswith("our-meals-photos-")

def test_s3_security():
    """Test S3 security configuration"""
    work = auto.LocalWorkspace()
    stack = auto.select_stack(stack_name="dev", work_dir=".")
    
    # Get the full stack deployment
    up_res = stack.up(on_output=print)
    
    # Test bucket configuration
    assert up_res.outputs["bucket_name"].value
    
    # Verify security settings are applied
    resources = up_res.resources
    bucket_resources = [r for r in resources if r.type == "aws:s3/bucket:Bucket"]
    assert len(bucket_resources) == 1
    
    bucket = bucket_resources[0]
    assert bucket.props["versioning"]["enabled"]
    assert bucket.props["serverSideEncryptionConfiguration"]
