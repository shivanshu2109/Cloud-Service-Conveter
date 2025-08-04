import json
from botocore.exceptions import ClientError

class ValidationHandler:
    def __init__(self, bedrock_client, config):
        self.bedrock_client = bedrock_client
        self.config = config
        self.required_keys = ['id', 'service', 'resource_type', 'region', 'quantity', 'configuration']
        
    def check_yaml_hierarchy_preservation(self, source_config, translated_config):
        """
        Ensures the translated YAML maintains the original structure and hierarchy.
        Enhanced to focus on structural integrity validation.
        """
        issues = []
        
        # Check if all required keys are present
        for key in self.required_keys:
            if key not in translated_config:
                issues.append(f"STRUCTURAL ERROR: Required key '{key}' is missing from translated configuration.")
        
        # Validate service and resource_type conversion
        if 'service' in source_config and 'service' in translated_config:
            if translated_config['service'] == source_config['service']:
                issues.append(f"SERVICE ERROR: Service name '{translated_config['service']}' was not converted from source cloud format.")
        
        if 'resource_type' in source_config and 'resource_type' in translated_config:
            if translated_config['resource_type'] == source_config['resource_type']:
                issues.append(f"RESOURCE ERROR: Resource type '{translated_config['resource_type']}' was not converted from source cloud format.")
        
        # Check for extra keys that weren't in the original
        source_keys = set(source_config.keys())
        translated_keys = set(translated_config.keys())
        extra_keys = translated_keys - source_keys
        
        if extra_keys:
            issues.append(f"STRUCTURAL WARNING: Extra keys found in translated configuration: {list(extra_keys)}")
        
        # Enhanced nested structure preservation check
        if 'configuration' in source_config and 'configuration' in translated_config:
            self._validate_configuration_structure(source_config['configuration'], 
                                                  translated_config['configuration'], issues)
        elif 'configuration' in source_config:
            issues.append("STRUCTURAL ERROR: Configuration section is missing in translated output.")
        
        return issues
    
    def _validate_configuration_structure(self, source_config, translated_config, issues):
        """
        Recursively validate configuration structure and service-specific settings.
        """
        if not isinstance(source_config, dict) or not isinstance(translated_config, dict):
            issues.append("STRUCTURAL ERROR: Configuration must be a dictionary/object.")
            return
        
        # Check for missing configuration keys
        source_config_keys = set(source_config.keys())
        translated_config_keys = set(translated_config.keys())
        
        missing_config_keys = source_config_keys - translated_config_keys
        if missing_config_keys:
            issues.append(f"CONFIGURATION ERROR: Missing configuration keys: {list(missing_config_keys)}")
        
        # Validate each configuration setting conversion
        for key, source_value in source_config.items():
            if key in translated_config:
                translated_value = translated_config[key]
                
                # Check if values are identical (might indicate incomplete translation)
                if source_value == translated_value and isinstance(source_value, str):
                    # Allow identical values for generic settings like names, but flag cloud-specific ones
                    if any(cloud in str(source_value).lower() for cloud in ['aws', 'azure', 'gcp', 'ec2', 'vm', 'compute']):
                        issues.append(f"CONVERSION WARNING: Configuration '{key}' may not be properly converted: '{source_value}'")
                
                # Recursively check nested configurations
                if isinstance(source_value, dict) and isinstance(translated_value, dict):
                    self._validate_configuration_structure(source_value, translated_value, issues)

    def validate_with_llm(self, source_config, translated_config, source_cloud, target_cloud, model_info):
        """
        Uses an LLM to perform a detailed validation of a translation.
        Enhancements include structural integrity checks, data mismatches, and null/empty value checks.
        """
        if not self.bedrock_client:
            return {"error": "Bedrock client not initialized."}
        
        if isinstance(translated_config, dict) and "error" in translated_config:
            return {
                "confidence_score": 0,
                "issues": [f"Initial translation failed: {translated_config['error']}"],
                "suggested_correction": None
            }
        
        issues = []
        
        # 1. Perform initial structural pre-checks to include in LLM validation
        hierarchy_issues = self.check_yaml_hierarchy_preservation(source_config, translated_config)
        
        # Include all hierarchy issues (both critical and non-critical)
        issues.extend(hierarchy_issues)

        # Include some manual checks for improved diagnostics
        for key, value in translated_config.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(f"EMPTY VALUE: Key '{key}' has an empty or null value.")

        # Always proceed to LLM validation for comprehensive analysis
        # The LLM will provide the final confidence score and suggested corrections

        model_id = model_info['arn']
        prompt = self.config["validation_prompt_template"].format(
            source_cloud=source_cloud.upper(),
            target_cloud=target_cloud.upper(),
            source_config_json=json.dumps(source_config, indent=2),
            translated_config_json=json.dumps(translated_config, indent=2)
        )

        try:
            response = self.bedrock_client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=[{"text": "You are a helpful cloud validation expert."}],
                inferenceConfig={"maxTokens": 4096}
            )
            json_string = response['output']['message']['content'][0]['text']
            
            start_index = json_string.find('{')
            end_index = json_string.rfind('}')
            if start_index != -1 and end_index != -1:
                json_string = json_string[start_index : end_index + 1]
            else:
                return {"error": "No JSON object found in validation response"}
            
            return json.loads(json_string)

        except (ClientError, json.JSONDecodeError, KeyError) as e:
            # Fallback to local validation results if LLM call fails
            confidence_score = max(0, 100 - len(issues) * 10) if issues else 80
            
            return {
                "confidence_score": confidence_score,
                "issues": issues + [f"Note: LLM validation unavailable ({str(e)}), using local validation only"],
                "suggested_correction": translated_config if issues else None
            }
