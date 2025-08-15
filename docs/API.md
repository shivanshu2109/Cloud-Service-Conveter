# API Reference

## Overview

This document provides detailed API documentation for the core modules of the Cloud Configuration Translator & Validator system.

## Module Structure

### Core Modules
- `app.py` - Main Streamlit web application
- `llm_handler.py` - LLM interaction and response processing
- `cache_manager.py` - Advanced caching system
- `validator.py` - Hybrid validation engine

## llm_handler.py

### Functions

#### `load_cache(path: str) -> dict`
Safely loads translation cache from disk with error resilience.

**Parameters:**
- `path` (str): File system path to the cache file

**Returns:**
- `dict`: Dictionary containing cached translations or empty dict if unavailable

**Example:**
```python
cache_data = load_cache("cache/translations.json")
```

#### `save_cache(path: str, data: dict) -> None`
Persists translation cache to disk with directory creation.

**Parameters:**
- `path` (str): Target file path for the cache
- `data` (dict): Dictionary containing translation cache entries

#### `get_cache_key(service_block: dict) -> str`
Generates a unique cache identifier for cloud service configurations.

**Parameters:**
- `service_block` (dict): Cloud service configuration dictionary

**Returns:**
- `str`: Hexadecimal SHA-256 hash string for cache indexing

#### `load_yaml(path: str) -> dict`
Loads YAML configuration files for processing.

**Parameters:**
- `path` (str): File system path to the YAML file

**Returns:**
- `dict`: Dictionary representation of the YAML content

#### `save_yaml(path: str, data: dict) -> None`
Saves translated configurations to YAML files.

**Parameters:**
- `path` (str): Target file path for the YAML output
- `data` (dict): Configuration dictionary to save

#### `query_llm(service_block: dict, source_cloud: str, target_cloud: str, model_info: dict) -> dict`
Executes translation requests via AWS Bedrock Language Models.

**Parameters:**
- `service_block` (dict): Cloud service configuration to translate
- `source_cloud` (str): Origin cloud platform identifier
- `target_cloud` (str): Destination cloud platform identifier
- `model_info` (dict): Dictionary containing model ARN and metadata

**Returns:**
- `dict`: Dictionary containing translated configuration or error information

#### `get_translation(service_block: dict, source_cloud: str, target_cloud: str, model_info: dict) -> dict`
Main translation orchestrator with intelligent caching.

**Parameters:**
- `service_block` (dict): Cloud service configuration to translate
- `source_cloud` (str): Source cloud platform identifier
- `target_cloud` (str): Target cloud platform identifier
- `model_info` (dict): Model configuration dictionary with ARN and metadata

**Returns:**
- `dict`: Translated configuration dictionary or error information

## cache_manager.py

### CacheManager Class

Enterprise-grade caching system for translation services.

#### Constructor
```python
CacheManager(cache_dir: str = "cache")
```

**Parameters:**
- `cache_dir` (str): Directory path for cache storage

#### Methods

##### `check_cache(service_config: dict, input_content: str, source_cloud: str, target_cloud: str, model_arn: str) -> Tuple[bool, Optional[dict], str]`
Check if a translation exists in the cache.

**Returns:**
- `tuple`: (cache_hit, cached_result, cache_key)
  - `cache_hit` (bool): Whether a cache entry was found
  - `cached_result` (dict | None): The cached translation result
  - `cache_key` (str): The cache key for this request

##### `store_translation(cache_key: str, translation_result: dict, service_config: dict, source_cloud: str, target_cloud: str, model_arn: str) -> None`
Store a new translation result in cache.

##### `store_user_edit(cache_key: str, edited_translation: dict, original_translation: dict) -> None`
Store user's edited version of a translation.

##### `store_validation_acceptance(cache_key: str, accepted_translation: dict, original_translation: dict) -> None`
Store accepted validation suggestion and update main cache.

##### `get_cache_stats() -> dict`
Get cache statistics for monitoring.

**Returns:**
- `dict`: Statistics including total_translations, user_edited_count, cache_size_mb

##### `clear_cache(cache_type: str = "all") -> None`
Clear cache entries of specified type.

**Parameters:**
- `cache_type` (str): Type of cache to clear ("all", "translations", "edits")

## validator.py

### ValidationHandler Class

Advanced validation engine for cloud configuration translations.

#### Constructor
```python
ValidationHandler(bedrock_client, config)
```

**Parameters:**
- `bedrock_client`: AWS Bedrock runtime client for LLM interactions
- `config` (dict): Configuration dictionary containing validation settings and prompts

#### Methods

##### `check_yaml_hierarchy_preservation(source_config: dict, translated_config: dict) -> list`
Ensures the translated YAML maintains the original structure and hierarchy.

**Parameters:**
- `source_config` (dict): Original cloud configuration
- `translated_config` (dict): Translated cloud configuration

**Returns:**
- `list`: List of validation issues found

##### `validate_with_llm(source_config: dict, translated_config: dict, source_cloud: str, target_cloud: str, model_info: dict) -> dict`
Uses an LLM to perform detailed validation of a translation.

**Parameters:**
- `source_config` (dict): Original cloud configuration
- `translated_config` (dict): Translated cloud configuration
- `source_cloud` (str): Source cloud platform identifier
- `target_cloud` (str): Target cloud platform identifier
- `model_info` (dict): Model configuration dictionary

**Returns:**
- `dict`: Validation report with confidence_score, issues, and suggested_correction

## app.py

### Main Application Functions

#### `reorder_dict(data: dict) -> dict`
Ensures consistent field ordering in cloud configuration objects.

#### `detect_changes(original: dict, modified: dict, path: str = "") -> dict`
Detect changes between two dictionaries and return change information.

#### `accept_suggestion_callback(item_index: int, correction: dict, source_cloud: str, target_cloud: str, model_info: dict) -> None`
Saves the corrected translation to the cache and updates the UI state.

## Configuration Structure

### config.json Schema

```json
{
  "aws_region": "us-east-1",
  "cache_dir": "cache",
  "available_models": {
    "Model Name": {
      "arn": "model-arn",
      "family": "model-family"
    }
  },
  "system_prompt": "...",
  "user_prompt_template": "...",
  "validation_prompt_template": "..."
}
```

### Model Configuration

Each model in `available_models` must have:
- `arn`: AWS Bedrock model ARN
- `family`: Model family (anthropic, meta, amazon, etc.)

## Error Handling

### Common Error Types

#### Translation Errors
- `"error": "Bedrock client not initialized."`
- `"error": "AI returned an empty response."`
- `"error": "No JSON object found in response"`
- `"error": "API or JSON parsing error: {details}"`

#### Validation Errors
- `"error": "Bedrock client not initialized."`
- `"error": "No JSON object found in validation response"`

### Error Recovery

The system implements comprehensive error handling:
1. **Graceful Fallbacks**: Local validation when LLM unavailable
2. **Cache Resilience**: Continue operation even with corrupted cache
3. **User Feedback**: Clear error messages with suggested actions

## Usage Examples

### Basic Translation
```python
from llm_handler import get_translation

service_config = {
    "id": "web-server",
    "service": "ec2",
    "resource_type": "instance",
    # ... more config
}

model_info = {
    "arn": "arn:aws:bedrock:us-east-1::model/claude-3-sonnet",
    "family": "anthropic"
}

result = get_translation(service_config, "aws", "gcp", model_info)
```

### Cache Management
```python
from cache_manager import CacheManager

cache = CacheManager("cache")
stats = cache.get_cache_stats()
print(f"Total translations: {stats['total_translations']}")
```

### Validation
```python
from validator import ValidationHandler

validator = ValidationHandler(bedrock_client, config)
report = validator.validate_with_llm(source, translated, "aws", "gcp", model_info)
print(f"Confidence: {report['confidence_score']}%")
```

## Performance Considerations

### Caching Strategy
- Hash-based cache keys for deterministic lookups
- Metadata storage for analytics and cleanup
- User edit tracking with rollback capabilities

### Cost Optimization
- Cache before expensive LLM calls
- Batch processing for multiple resources
- Optional validation to reduce API usage

### Memory Management
- Streaming file processing for large configurations
- Efficient JSON serialization
- Automatic cache cleanup policies
