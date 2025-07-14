import os
import json
from hashlib import sha256
import boto3
from botocore.exceptions import ClientError
from utils import load_cache, save_cache, get_cache_key
# At the top of llm_handler.py
import streamlit as st

# This will use Streamlit's secrets when deployed, and a local .env file when run locally
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
# --- Load Configuration from JSON File ---
with open('config.json', 'r') as f:
    config = json.load(f)

# --- Use Loaded Configuration ---
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", config.get("aws_region"))
MODEL_ID = config.get("model_id")
CACHE_DIR = config.get("cache_dir")
PROMPT_TEMPLATE = config.get("prompt_template")

try:
    bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=AWS_REGION)
    os.makedirs(CACHE_DIR, exist_ok=True)
except Exception as e:
    print(f"❌ Error creating Bedrock client: {e}")
    bedrock_client = None

# --- Generic LLM Query Function ---
def query_llm(service_block, source_cloud, target_cloud):
    prompt = PROMPT_TEMPLATE.format(
        source_cloud=source_cloud.upper(),
        target_cloud=target_cloud.upper(),
        service_block_json=json.dumps(service_block, indent=2)
    )

    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }
    request_body = json.dumps(native_request)

    try:
        response = bedrock_client.invoke_model(
            modelId=MODEL_ID,
            body=request_body,
            contentType="application/json",
            accept="application/json"
        )
        response_body = json.loads(response.get("body").read())
        json_string = response_body["content"][0]["text"]
        
        if json_string.strip().startswith("```json"):
            start = json_string.find('{')
            end = json_string.rfind('}')
            if start != -1 and end != -1:
                json_string = json_string[start:end+1]
        
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            print("❌ LLM Error: AI did not return a valid JSON object.")
            print("\n--- PROBLEMATIC STRING FROM LLM ---")
            print(json_string)
            print("--- END OF PROBLEMATIC STRING ---\n")
            return {"error": f"Invalid JSON from AI: {e}"}

    except ClientError as e:
        print(f"❌ Bedrock Error: {e}")
        return {"error": "Bedrock failed to respond."}
    
# for app.py
def get_cache_path(source_cloud, target_cloud):
    """Returns the cache path for a given translation direction."""
    return os.path.join(CACHE_DIR, f"{source_cloud}_to_{target_cloud}_cache.json")

# --- UPDATE THE get_translation FUNCTION ---
def get_translation(service_block, source_cloud, target_cloud):
    if not bedrock_client:
        return {"error": "Bedrock client not initialized."}

    # Use the new helper function to get the cache path
    cache_path = get_cache_path(source_cloud, target_cloud)
    cache = load_cache(cache_path)
# till here


# --- Generic Main Translator Function (Updated) ---
def get_translation(service_block, source_cloud, target_cloud):
    if not bedrock_client:
        return {"error": "Bedrock client not initialized."}

    cache_path = os.path.join(CACHE_DIR, f"{source_cloud}_to_{target_cloud}_cache.json")
    cache = load_cache(cache_path)
    key = get_cache_key(service_block)

    if key in cache:
        print(f"✅ Cache hit for: {service_block.get('id')}")
        return cache[key]

    print(f"⚠️  Cache miss → Querying Bedrock for: {service_block.get('id')}")
    # The result_dict is now the final translation, not a nested object
    result_dict = query_llm(service_block, source_cloud, target_cloud)
    
    if "error" not in result_dict:
        cache[key] = result_dict
        save_cache(cache_path, cache)
        
    return result_dict