#!/usr/bin/env python3
"""
Test script to verify validation functionality works correctly
"""

import json
import boto3
from validator import ValidationHandler

def test_validation():
    """Test the validation functionality"""
    
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Initialize Bedrock client
    try:
        bedrock_client = boto3.client(
            service_name="bedrock-runtime", 
            region_name=config.get("aws_region")
        )
        print("Bedrock client initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Bedrock client: {e}")
        return False
    
    # Initialize validator
    validator = ValidationHandler(bedrock_client, config)
    print("Validator initialized successfully")
    
    # Test data
    source_config = {
        "id": "test-ec2-instance",
        "service": "EC2",
        "resource_type": "Instance",
        "region": "us-east-1",
        "quantity": 1,
        "configuration": {
            "instance_type": "t3.micro",
            "ami_id": "ami-12345678",
            "security_groups": ["sg-123456"]
        }
    }
    
    translated_config = {
        "id": "test-ec2-instance",
        "service": "Compute Engine",
        "resource_type": "VM Instance",
        "region": "us-central1-a",
        "quantity": 1,
        "configuration": {
            "machine_type": "e2-micro",
            "image": "ubuntu-2004-focal-v20210315",
            "firewall_rules": ["default-allow-internal"]
        }
    }
    
    # Model info
    model_info = list(config["available_models"].values())[0]  # Use first available model
    
    print(f"Testing validation with model: {list(config['available_models'].keys())[0]}")
    
    # Test validation
    try:
        result = validator.validate_with_llm(
            source_config, 
            translated_config, 
            "aws", 
            "gcp", 
            model_info
        )
        
        if "error" in result:
            print(f"Validation returned error: {result['error']}")
            return False
        
        print("Validation completed successfully!")
        print(f"Confidence Score: {result.get('confidence_score', 'N/A')}%")
        
        issues = result.get('issues', [])
        if issues:
            print(f"Found {len(issues)} validation issues:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
        else:
            print("No validation issues found!")
        
        if result.get('suggested_correction'):
            print("AI suggested corrections available")
        
        return True
        
    except Exception as e:
        print(f"Validation test failed with exception: {e}")
        return False

if __name__ == "__main__":
    print("Testing Cloud Converter Validation System...")
    print("=" * 50)
    
    success = test_validation()
    
    print("=" * 50)
    if success:
        print("All validation tests passed!")
    else:
        print("Validation tests failed!")
