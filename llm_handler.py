import os
import json
from hashlib import sha256
import boto3
from botocore.exceptions import ClientError
from utils import load_cache, save_cache, get_cache_key

# --- Load Configuration ---
with open('config.json', 'r') as f:
    config = json.load(f)

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", config.get("aws_region"))
CACHE_DIR = config.get("cache_dir")
# --- NEW: Load both system and user prompts ---
SYSTEM_PROMPT = config.get("system_prompt")
USER_PROMPT_TEMPLATE = config.get("user_prompt_template")

try:
    bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=AWS_REGION)
    os.makedirs(CACHE_DIR, exist_ok=True)
except Exception as e:
    print(f"❌ Error creating Bedrock client: {e}")
    bedrock_client = None

# --- LLM Query Function (Updated to use the 'converse' API) ---
def query_llm(service_block, source_cloud, target_cloud, model_info):
    model_id = model_info['arn'] # Use ARN for provisioned, ID for on-demand
    
    # Create the user-specific part of the prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        source_cloud=source_cloud.upper(),
        target_cloud=target_cloud.upper(),
        service_block_json=json.dumps(service_block, indent=2)
    )

    try:
        # Use the more robust 'converse' API
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}],
                }
            ],
            system=[
                {
                    "text": SYSTEM_PROMPT,
                }
            ],
            inferenceConfig={"maxTokens": 4096}
        )
        
        # Parse the response structure from the 'converse' API
        json_string = response['output']['message']['content'][0]['text']
        
        if not json_string:
             return {"error": "AI returned an empty response."}

        # Robustly find and extract the JSON object from the response string
        start_index = json_string.find('{')
        end_index = json_string.rfind('}')
        if start_index != -1 and end_index != -1:
            json_string = json_string[start_index : end_index + 1]
        else:
            return {"error": "No JSON object found in response"}

        # --- THIS IS THE FIX: Add debugging for JSON parsing errors ---
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            print("❌ LLM Error: AI did not return a valid JSON object.")
            print("\n--- PROBLEMATIC STRING FROM LLM ---")
            print(json_string)
            print("--- END OF PROBLEMATIC STRING ---\n")
            return {"error": f"Invalid JSON from AI: {e}"}
        # --- END OF FIX ---

    except ClientError as e:
        return {"error": f"Bedrock API Error: {e}"}

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
        print(f"✅ Cache hit for: {service_block.get('id')} using model with ARN: {model_id}")
        return cache[key]

    print(f"⚠️  Cache miss → Querying Bedrock for: {service_block.get('id')} using model with ARN: {model_id}")
    result_dict = query_llm(service_block, source_cloud, target_cloud, model_info)
    
    if "error" not in result_dict:
        cache[key] = result_dict
        save_cache(cache_path, cache)
        
    return result_dict

# --- Helper for UI ---
def get_cache_path(source_cloud, target_cloud, model_arn):
    sanitized_arn = model_arn.replace(':', '_').replace('/', '_')
    return os.path.join(CACHE_DIR, f"{source_cloud}_to_{target_cloud}_{sanitized_arn}.json")
