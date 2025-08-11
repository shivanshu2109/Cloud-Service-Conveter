import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple


class CacheManager:
    """
    Simple, unified caching system for translation service that handles:
    - Single cache file with clear structure
    - Easy-to-understand cache entries
    - Automatic cache updates and removals
    - User edit tracking with version control
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        
        # Single cache file path
        self.cache_file = os.path.join(cache_dir, "translations_cache.json")
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
            
        # Initialize cache if it doesn't exist
        self._initialize_cache()
    
    def _generate_cache_key(self, service_config: Dict[str, Any], input_content: str, 
                          source_cloud: str, target_cloud: str, model_arn: str) -> str:
        """
        Generate a unique cache key based on service configuration, input file, 
        and translation parameters.
        """
        # Create a composite key from all relevant parameters
        key_components = {
            "service_config": service_config,
            "input_content": hashlib.sha256(input_content.encode()).hexdigest(),
            "source_cloud": source_cloud,
            "target_cloud": target_cloud,
            "model_arn": model_arn
        }
        
        # Create a deterministic hash
        key_string = json.dumps(key_components, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _initialize_cache(self):
        """Initialize the cache file if it doesn't exist."""
        if not os.path.exists(self.cache_file):
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def update_cache(self, cache_key: str, data: Dict[str, Any]):
        """Updates the cache with the latest translation result."""
        with open(self.cache_file, 'r+', encoding='utf-8') as f:
            cache_data = json.load(f)
            cache_data[cache_key] = data
            f.seek(0)
            json.dump(cache_data, f, indent=2)
            f.truncate()

    def check_cache(self, service_config: Dict[str, Any], input_content: str,
                   source_cloud: str, target_cloud: str, model_arn: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Check if a translation exists in the cache.
        
        Returns:
            - cache_hit (bool): Whether a cache entry was found
            - cached_result (Dict): The cached translation result (None if no hit)
            - cache_key (str): The cache key for this request
        """
        cache_key = self._generate_cache_key(service_config, input_content, source_cloud, target_cloud, model_arn)
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                if cache_key in cache_data:
                    return True, cache_data[cache_key]["translation"], cache_key
        except (json.JSONDecodeError, IOError):
            pass  # Cache is corrupted, so treat as no hit

        return False, None, cache_key
        
    def store_translation(self, cache_key: str, translation_result: Dict[str, Any],
                         service_config: Dict[str, Any], source_cloud: str, 
                         target_cloud: str, model_arn: str):
        """Store a new translation result in cache and update cache."""
        cache_entry = {
            "translation": translation_result,
            "timestamp": datetime.utcnow().isoformat(),
            "service_config": service_config,
            "source_cloud": source_cloud,
            "target_cloud": target_cloud,
            "model_arn": model_arn,
            "version": "1.0"
        }
        
        self.update_cache(cache_key, cache_entry)

    def store_user_edit(self, cache_key: str, edited_translation: Dict[str, Any], 
                       original_translation: Dict[str, Any]):
        """Store user's edited version of a translation and update cache."""
        edit_entry = {
            "translation": edited_translation,
            "original_translation": original_translation,
            "edited_timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        self.update_cache(cache_key, edit_entry) # Update cache with user edit
        
    
    def store_validation_acceptance(self, cache_key: str, accepted_translation: Dict[str, Any],
                                  original_translation: Dict[str, Any]):
        """Store accepted validation suggestion and update main cache."""
        # Load existing cache entry to preserve metadata
        existing_entry = self._load_cache_entry(cache_key, "translations")
        if existing_entry:
            # Preserve all existing metadata but update translation
            validation_entry = existing_entry.copy()
            validation_entry.update({
                "translation": accepted_translation,
                "original_translation": original_translation,
                "validation_accepted_timestamp": datetime.utcnow().isoformat(),
                "validation_accepted": True,
                "last_accessed": datetime.utcnow().isoformat()
            })
        else:
            # Create new entry if none exists
            validation_entry = {
                "translation": accepted_translation,
                "original_translation": original_translation,
                "validation_accepted_timestamp": datetime.utcnow().isoformat(),
                "validation_accepted": True,
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
        
        # Update the main cache directly with the corrected translation
        self.update_cache(cache_key, validation_entry)
        
        print(f"✅ Cache updated with validation acceptance for key: {cache_key[:16]}...")
        print(f"   Corrected translation ID: {accepted_translation.get('id', 'Unknown')}")
    
    def update_access_count(self, cache_key: str):
        """Update access count and timestamp for cache analytics."""
        metadata = self._load_cache_entry(cache_key, "metadata") or {}
        metadata.update({
            "access_count": metadata.get("access_count", 0) + 1,
            "last_accessed": datetime.utcnow().isoformat()
        })
        self._save_cache_entry(cache_key, metadata, "metadata")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        stats = {
            "total_translations": 0,
            "user_edited_count": 0,
            "cache_size_mb": 0
        }

        # Calculate total cache size and number of entries
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                stats["total_translations"] = len(cache_data)
                # Count user edited entries
                user_edited = sum(1 for entry in cache_data.values() 
                                if entry.get("edited_timestamp") or entry.get("validation_accepted_timestamp"))
                stats["user_edited_count"] = user_edited
                
                total_size = os.path.getsize(self.cache_file)
                stats["cache_size_mb"] = round(total_size / (1024 * 1024), 2)
        except (json.JSONDecodeError, IOError):
            pass  # Handle any errors quietly

        return stats
    
    def clear_cache(self, cache_type: str = "all"):
        """Clear cache entries of specified type and update main cache."""
        if cache_type == "all":
            # Clear entire cache file
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        elif cache_type == "translations":
            # Clear entire cache file for translations
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        elif cache_type == "edits":
            # Remove only user-edited entries
            try:
                with open(self.cache_file, 'r+', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # Keep only entries that were not user-edited
                    filtered_data = {
                        k: v for k, v in cache_data.items() 
                        if not (v.get("edited_timestamp") or v.get("validation_accepted_timestamp"))
                    }
                    f.seek(0)
                    json.dump(filtered_data, f, indent=2)
                    f.truncate()
            except (json.JSONDecodeError, IOError):
                pass  # Handle errors gracefully
    
    def invalidate_cache_entry(self, cache_key: str):
        """Invalidate a specific cache entry and remove from cache."""
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, 'r+', encoding='utf-8') as f:
                cache_data = json.load(f)
                if cache_key in cache_data:
                    del cache_data[cache_key]
                    f.seek(0)
                    json.dump(cache_data, f, indent=2)
                    f.truncate()
        except (json.JSONDecodeError, IOError):
            pass  # Ignore errors if the cache is corrupted
    
    # Add missing helper methods that are referenced in the code
    def _save_cache_entry(self, cache_key: str, entry: Dict[str, Any], cache_type: str):
        """Helper method to save cache entry (placeholder implementation)."""
        # For now, just update the main cache
        self.update_cache(cache_key, entry)
    
    def _load_cache_entry(self, cache_key: str, cache_type: str) -> Optional[Dict[str, Any]]:
        """Helper method to load cache entry (placeholder implementation)."""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data.get(cache_key)
        except (json.JSONDecodeError, IOError):
            return None
    
    def _update_main_cache(self, cache_key: str, entry: Dict[str, Any]):
        """Helper method to update main cache (placeholder implementation)."""
        self.update_cache(cache_key, entry)
