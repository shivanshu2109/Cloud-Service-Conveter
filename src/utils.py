"""
Cloud Configuration Utilities Module

A comprehensive collection of utility functions for cloud configuration processing,
YAML operations, caching, and data manipulation. Provides reusable components
for the Cloud Configuration Translator & Validator application.

Key Features:
- YAML file operations with error handling
- Cache management utilities
- Configuration data processing
- String and data type utilities
- File system operations
- Hashing and key generation

Author: Cloud Migration Intern Team
Version: 1.0.0
Last Updated: August 2025
"""

import os
import json
import yaml
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path


# ================================
# YAML OPERATIONS
# ================================

def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Loads YAML configuration files with comprehensive error handling.
    
    Provides a safe interface for reading cloud configuration files
    and converting them to Python dictionaries for manipulation.
    
    Args:
        file_path: File system path to the YAML file
        
    Returns:
        Dictionary representation of the YAML content
        
    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        yaml.YAMLError: If the YAML content is malformed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML syntax in {file_path}: {e}")


def save_yaml(file_path: str, data: Dict[str, Any], create_dirs: bool = True) -> None:
    """
    Saves configuration dictionaries to properly formatted YAML files.
    
    Writes cloud configuration dictionaries to YAML files while preserving
    the original key order for better readability and consistency.
    
    Args:
        file_path: Target file path for the YAML output
        data: Configuration dictionary to save
        create_dirs: Whether to create parent directories if they don't exist
        
    Raises:
        IOError: If the file cannot be written
        yaml.YAMLError: If the data cannot be serialized to YAML
    """
    if create_dirs:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, indent=2, sort_keys=False, default_flow_style=False)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Cannot serialize data to YAML: {e}")
    except IOError as e:
        raise IOError(f"Cannot write to file {file_path}: {e}")


def validate_yaml_structure(data: Dict[str, Any], required_keys: List[str]) -> List[str]:
    """
    Validates YAML structure against required keys and common patterns.
    
    Args:
        data: Dictionary to validate
        required_keys: List of keys that must be present
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if not isinstance(data, dict):
        errors.append("Root element must be a dictionary/object")
        return errors
    
    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: '{key}'")
    
    return errors


# ================================
# JSON OPERATIONS
# ================================

def load_json(file_path: str) -> Dict[str, Any]:
    """
    Safely loads JSON files with error handling.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing JSON data or empty dict if file doesn't exist
        
    Raises:
        json.JSONDecodeError: If JSON is malformed
    """
    if not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in {file_path}: {e}")


def save_json(file_path: str, data: Dict[str, Any], create_dirs: bool = True, indent: int = 2) -> None:
    """
    Saves data to JSON file with formatting.
    
    Args:
        file_path: Target file path
        data: Data to save
        create_dirs: Whether to create parent directories
        indent: JSON indentation level
        
    Raises:
        IOError: If file cannot be written
    """
    if create_dirs:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    except IOError as e:
        raise IOError(f"Cannot write to file {file_path}: {e}")


# ================================
# HASHING AND KEY GENERATION
# ================================

def generate_hash(data: Union[str, Dict[str, Any]], algorithm: str = 'sha256') -> str:
    """
    Generates hash for data using specified algorithm.
    
    Args:
        data: String or dictionary to hash
        algorithm: Hash algorithm to use ('sha256', 'md5', etc.)
        
    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, dict):
        data_string = json.dumps(data, sort_keys=True)
    else:
        data_string = str(data)
    
    hash_func = getattr(hashlib, algorithm)()
    hash_func.update(data_string.encode('utf-8'))
    return hash_func.hexdigest()


def generate_cache_key(service_config: Dict[str, Any], input_content: str, 
                      source_cloud: str, target_cloud: str, model_arn: str) -> str:
    """
    Generates a unique cache key for translation requests.
    
    Creates a composite key from all relevant parameters to ensure
    accurate cache lookups and prevent duplicate translations.
    
    Args:
        service_config: Service configuration dictionary
        input_content: Original input content
        source_cloud: Source cloud platform
        target_cloud: Target cloud platform
        model_arn: Model ARN used for translation
        
    Returns:
        SHA-256 hash string for cache indexing
    """
    key_components = {
        "service_config": service_config,
        "input_content": generate_hash(input_content),
        "source_cloud": source_cloud,
        "target_cloud": target_cloud,
        "model_arn": model_arn
    }
    
    return generate_hash(key_components)


# ================================
# DATA STRUCTURE UTILITIES
# ================================

def reorder_dict(data: Dict[str, Any], desired_order: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Ensures consistent field ordering in cloud configuration objects.
    
    Maintains a standardized structure across all cloud providers by enforcing
    a specific key order that prioritizes essential identification and 
    configuration fields for better readability and consistency.
    
    Args:
        data: Dictionary containing cloud resource configuration
        desired_order: List of keys in desired order (uses default if None)
        
    Returns:
        Reordered dictionary with standardized field sequence
    """
    if not isinstance(data, dict):
        return data
    
    if desired_order is None:
        desired_order = ["id", "service", "resource_type", "region", "quantity", "configuration"]
    
    # Create ordered dict with desired keys first
    ordered_data = {}
    for key in desired_order:
        if key in data:
            ordered_data[key] = data[key]
    
    # Add any remaining keys
    for key, value in data.items():
        if key not in ordered_data:
            ordered_data[key] = value
    
    return ordered_data


def detect_changes(original: Dict[str, Any], modified: Dict[str, Any], path: str = "") -> Dict[str, List]:
    """
    Detect changes between two dictionaries and return detailed change information.
    
    Args:
        original: Original dictionary
        modified: Modified dictionary
        path: Current path in nested structure
        
    Returns:
        Dictionary containing lists of added, removed, modified, and unchanged items
    """
    changes = {
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged": []
    }
    
    # Get all keys from both dictionaries
    all_keys = set(original.keys()) | set(modified.keys())
    
    for key in all_keys:
        current_path = f"{path}.{key}" if path else key
        
        if key not in original:
            changes["added"].append({"path": current_path, "value": modified[key]})
        elif key not in modified:
            changes["removed"].append({"path": current_path, "value": original[key]})
        elif original[key] != modified[key]:
            if isinstance(original[key], dict) and isinstance(modified[key], dict):
                # Recursively detect changes in nested dictionaries
                nested_changes = detect_changes(original[key], modified[key], current_path)
                for change_type, change_list in nested_changes.items():
                    changes[change_type].extend(change_list)
            else:
                changes["modified"].append({
                    "path": current_path,
                    "old_value": original[key],
                    "new_value": modified[key]
                })
        else:
            changes["unchanged"].append({"path": current_path, "value": original[key]})
    
    return changes


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries, with dict2 taking precedence.
    
    Args:
        dict1: Base dictionary
        dict2: Dictionary to merge (takes precedence)
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


# ================================
# FILE SYSTEM UTILITIES
# ================================

def ensure_directory(directory_path: str) -> None:
    """
    Ensures a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
    """
    os.makedirs(directory_path, exist_ok=True)


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in MB, or 0 if file doesn't exist
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    except OSError:
        return 0.0


def clean_filename(filename: str) -> str:
    """
    Clean filename by removing or replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename safe for file system
    """
    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not empty
    if not filename:
        filename = "untitled"
    
    return filename


def get_timestamp_string(format_str: str = "%Y%m%d_%H%M%S") -> str:
    """
    Get current timestamp as formatted string.
    
    Args:
        format_str: strftime format string
        
    Returns:
        Formatted timestamp string
    """
    return datetime.now().strftime(format_str)


# ================================
# STRING UTILITIES
# ================================

def sanitize_identifier(identifier: str) -> str:
    """
    Sanitize string to be used as file identifier or cache key.
    
    Args:
        identifier: String to sanitize
        
    Returns:
        Sanitized string safe for use as identifier
    """
    # Replace common problematic characters
    replacements = {':': '_', '/': '_', '\\': '_', '.': '_', ' ': '_'}
    
    result = identifier
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    # Remove any remaining special characters except alphanumeric and underscores
    result = ''.join(c for c in result if c.isalnum() or c == '_')
    
    return result


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to specified length with optional suffix.
    
    Args:
        text: String to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append to truncated strings
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


# ================================
# VALIDATION UTILITIES
# ================================

def validate_cloud_provider(provider: str) -> bool:
    """
    Validate if provider is a supported cloud platform.
    
    Args:
        provider: Cloud provider string
        
    Returns:
        True if provider is supported, False otherwise
    """
    supported_providers = {'aws', 'azure', 'gcp'}
    return provider.lower() in supported_providers


def validate_required_keys(data: Dict[str, Any], required_keys: List[str]) -> List[str]:
    """
    Validate that required keys exist in dictionary.
    
    Args:
        data: Dictionary to validate
        required_keys: List of required keys
        
    Returns:
        List of missing keys (empty if all present)
    """
    missing_keys = []
    for key in required_keys:
        if key not in data:
            missing_keys.append(key)
    
    return missing_keys


def is_empty_value(value: Any) -> bool:
    """
    Check if a value is empty (None, empty string, empty container, etc.).
    
    Args:
        value: Value to check
        
    Returns:
        True if value is considered empty, False otherwise
    """
    if value is None:
        return True
    
    if isinstance(value, str):
        return not value.strip()
    
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    
    return False


# ================================
# LOGGING AND DEBUG UTILITIES
# ================================

def format_exception_details(exception: Exception) -> Dict[str, str]:
    """
    Format exception details into a structured dictionary.
    
    Args:
        exception: Exception instance
        
    Returns:
        Dictionary with exception details
    """
    return {
        "type": type(exception).__name__,
        "message": str(exception),
        "timestamp": datetime.utcnow().isoformat()
    }


def log_operation_timing(operation_name: str, start_time: float, end_time: float) -> Dict[str, Any]:
    """
    Create a timing log entry for operations.
    
    Args:
        operation_name: Name of the operation
        start_time: Start time (from time.time())
        end_time: End time (from time.time())
        
    Returns:
        Dictionary with timing information
    """
    duration = end_time - start_time
    return {
        "operation": operation_name,
        "duration_seconds": round(duration, 3),
        "timestamp": datetime.utcnow().isoformat()
    }


# ================================
# CACHE UTILITIES
# ================================

def create_cache_metadata(timestamp: Optional[str] = None, version: str = "1.0") -> Dict[str, str]:
    """
    Create standard cache metadata structure.
    
    Args:
        timestamp: ISO timestamp string (current time if None)
        version: Cache entry version
        
    Returns:
        Dictionary with cache metadata
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    
    return {
        "timestamp": timestamp,
        "version": version,
        "last_accessed": timestamp
    }


def is_cache_expired(cache_entry: Dict[str, Any], max_age_hours: int = 24) -> bool:
    """
    Check if a cache entry has expired.
    
    Args:
        cache_entry: Cache entry dictionary
        max_age_hours: Maximum age in hours
        
    Returns:
        True if cache entry is expired, False otherwise
    """
    if "timestamp" not in cache_entry:
        return True
    
    try:
        entry_time = datetime.fromisoformat(cache_entry["timestamp"])
        current_time = datetime.utcnow()
        age_hours = (current_time - entry_time).total_seconds() / 3600
        
        return age_hours > max_age_hours
    except (ValueError, TypeError):
        return True  # Invalid timestamp, consider expired
