import os
import json
from hashlib import sha256
import boto3
from botocore.exceptions import ClientError
import yaml

# Cache operations

def load_cache(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_cache(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_cache_key(service_block):
    raw = json.dumps(service_block, sort_keys=True)
    return sha256(raw.encode()).hexdigest()

# YAML operations

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def save_yaml(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        yaml.dump(data, f, indent=2, sort_keys=False)

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
    model_id = model_info['arn']
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        source_cloud=source_cloud.upper(),
        target_cloud=target_cloud.upper(),
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
    if not bedrock_client:
        return {"error": "Bedrock client not initialized."}

    model_id = model_info['arn']
    sanitized_id = model_id.replace(':', '_').replace('/', '_')
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
    sanitized_arn = model_arn.replace(':', '_').replace('/', '_')
    return os.path.join(CACHE_DIR, f"{source_cloud}_to_{target_cloud}_{sanitized_arn}.json")
