"""
LLM Handler Module

Handles all interactions with AWS Bedrock Language Models for cloud configuration
translation. Provides intelligent caching, prompt management, and response processing
to ensure efficient and accurate cross-cloud resource translations.

Key Features:
- Multi-model support (Claude, LLaMA, Nova)
- Intelligent response parsing and validation
- Comprehensive error handling
- YAML processing utilities

Author: Cloud Migration Intern Team
Version: 1.0.0
"""

import os
import json
from hashlib import sha256
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from utils import load_json, save_json, load_yaml, save_yaml, generate_hash, sanitize_identifier

# Load environment variables from .env file
load_dotenv()

# Cache Operations

def load_cache(path):
    """
    Safely loads translation cache from disk with error resilience.
    
    Uses the utility function from utils.py for consistent JSON handling.
    
    Args:
        path: File system path to the cache file
        
    Returns:
        Dictionary containing cached translations or empty dict if unavailable
    """
    return load_json(path)


def save_cache(path, data):
    """
    Persists translation cache to disk with directory creation.
    
    Uses the utility function from utils.py for consistent JSON handling.
    
    Args:
        path: Target file path for the cache
        data: Dictionary containing translation cache entries
    """
    save_json(path, data)


def get_cache_key(service_block):
    """
    Generates a unique cache identifier for cloud service configurations.
    
    Uses the utility function from utils.py for consistent hash generation.
    
    Args:
        service_block: Cloud service configuration dictionary
        
    Returns:
        Hexadecimal SHA-256 hash string for cache indexing
    """
    return generate_hash(service_block)

# YAML operations

# load_yaml function moved to utils.py


# save_yaml function moved to utils.py

# --- Load Configuration ---
with open('config.json', 'r') as f:
    config = json.load(f)

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", config.get("aws_region"))
CACHE_DIR = config.get("cache_dir")
SYSTEM_PROMPT = config.get("system_prompt")
USER_PROMPT_TEMPLATE = config.get("user_prompt_template")

try:
    bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=AWS_REGION)
    os.makedirs(CACHE_DIR, exist_ok=True)
except Exception as e:
    print(f"Error creating Bedrock client: {e}")
    bedrock_client = None

# --- LLM Query Function ---
def query_llm(service_block, source_cloud, target_cloud, model_info):
    """
    Executes translation requests via AWS Bedrock Language Models.
    
    Handles the complete LLM interaction workflow including prompt construction,
    API communication, response parsing, and error handling. Supports multiple
    model families through a unified interface.
    
    Args:
        service_block: Cloud service configuration to translate
        source_cloud: Origin cloud platform identifier
        target_cloud: Destination cloud platform identifier
        model_info: Dictionary containing model ARN and metadata
        
    Returns:
        Dictionary containing translated configuration or error information
    """
    model_id = model_info['arn']
    
    # Defensive type conversion to ensure string operations succeed
    source_cloud_str = str(source_cloud).lower() if source_cloud else "unknown"
    target_cloud_str = str(target_cloud).lower() if target_cloud else "unknown"
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        source_cloud=source_cloud_str.upper(),
        target_cloud=target_cloud_str.upper(),
        service_block_json=json.dumps(service_block, indent=2)
    )

    try:
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            system=[{"text": SYSTEM_PROMPT}],
            inferenceConfig={"maxTokens": 4096}
        )
        
        json_string = response['output']['message']['content'][0]['text']
        
        if not json_string:
             return {"error": "AI returned an empty response."}

        start_index = json_string.find('{')
        end_index = json_string.rfind('}')
        if start_index != -1 and end_index != -1:
            json_string = json_string[start_index : end_index + 1]
        else:
            return {"error": "No JSON object found in response"}

        return json.loads(json_string)

    except (ClientError, json.JSONDecodeError) as e:
        return {"error": f"API or JSON parsing error: {e}"}

# --- Main Translator Function ---
def get_translation(service_block, source_cloud, target_cloud, model_info):
    """
    Main translation orchestrator with intelligent caching.
    
    Coordinates the entire translation process, checking cache first to avoid
    redundant API calls, then processing new translations and storing results.
    Provides significant cost savings through cache optimization.
    
    Args:
        service_block: Cloud service configuration to translate
        source_cloud: Source cloud platform identifier
        target_cloud: Target cloud platform identifier
        model_info: Model configuration dictionary with ARN and metadata
        
    Returns:
        Translated configuration dictionary or error information
    """
    if not bedrock_client:
        return {"error": "Bedrock client not initialized."}

    model_id = model_info['arn']
    sanitized_id = sanitize_identifier(model_id)
    cache_path = os.path.join(CACHE_DIR, f"{source_cloud}_to_{target_cloud}_{sanitized_id}.json")
    
    cache = load_cache(cache_path)
    key = get_cache_key(service_block)

    if key in cache:
        return cache[key]

    result_dict = query_llm(service_block, source_cloud, target_cloud, model_info)
    
    # We only cache the initial translation. The corrected version will be cached by the UI.
    if "error" not in result_dict:
        cache[key] = result_dict
        save_cache(cache_path, cache)
        
    return result_dict

# --- Helper for UI ---
def get_cache_path(source_cloud, target_cloud, model_arn):
    """
    Generate cache file path for given translation parameters.
    
    Args:
        source_cloud: Source cloud provider
        target_cloud: Target cloud provider  
        model_arn: Model ARN to sanitize
        
    Returns:
        Path to cache file
    """
    sanitized_arn = sanitize_identifier(model_arn)
    return os.path.join(CACHE_DIR, f"{source_cloud}_to_{target_cloud}_{sanitized_arn}.json")
