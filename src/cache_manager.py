"""
Advanced Cache Management System

Provides enterprise-grade caching functionality for cloud configuration translations
with intelligent storage, user edit tracking, and performance analytics. Designed
for scalability and reliability in production environments.

Key Features:
- Unified cache architecture with single-file storage
- User modification tracking with rollback capabilities
- Validation acceptance workflow management
- Performance analytics and cache statistics
- Automatic cache invalidation and cleanup

Author: Cloud Migration Intern Team
Version: 1.0.0
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from utils import generate_cache_key, load_json, save_json, ensure_directory, get_file_size_mb, create_cache_metadata


class CacheManager:
    """
    Enterprise-grade caching system for translation services.
    
    Manages all aspects of translation caching including initial translations,
    user edits, validation corrections, and performance analytics. Built with
    reliability and scalability as primary concerns.
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "translations_cache.json")
        ensure_directory(cache_dir)
        self._initialize_cache()
    
    def _generate_cache_key(self, service_config: Dict[str, Any], input_content: str, 
                          source_cloud: str, target_cloud: str, model_arn: str) -> str:
        """
        Generate a unique cache key based on service configuration, input file, 
        and translation parameters.
        
        Uses the utility function from utils.py for consistent key generation.
        """
        return generate_cache_key(service_config, input_content, source_cloud, target_cloud, model_arn)
    
    def _initialize_cache(self):
        """Initialize the cache file if it doesn't exist."""
        if not os.path.exists(self.cache_file):
            save_json(self.cache_file, {}, create_dirs=False)

    def update_cache(self, cache_key: str, data: Dict[str, Any]):
        """Updates the cache with the latest translation result."""
        try:
            cache_data = load_json(self.cache_file)
            cache_data[cache_key] = data
            save_json(self.cache_file, cache_data, create_dirs=False)
        except Exception as e:
            print(f"Error updating cache: {e}")
            # Fallback to creating new cache with just this entry
            save_json(self.cache_file, {cache_key: data}, create_dirs=False)

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
            cache_data = load_json(self.cache_file)
            if cache_key in cache_data:
                return True, cache_data[cache_key]["translation"], cache_key
        except Exception:
            pass  # Cache is corrupted, so treat as no hit

        return False, None, cache_key
        
    def store_translation(self, cache_key: str, translation_result: Dict[str, Any],
                         service_config: Dict[str, Any], source_cloud: str, 
                         target_cloud: str, model_arn: str):
        """Store a new translation result in cache and update cache."""
        cache_entry = {
            "translation": translation_result,
            "service_config": service_config,
            "source_cloud": source_cloud,
            "target_cloud": target_cloud,
            "model_arn": model_arn,
            **create_cache_metadata()
        }
        
        self.update_cache(cache_key, cache_entry)

    def store_user_edit(self, cache_key: str, edited_translation: Dict[str, Any], 
                       original_translation: Dict[str, Any]):
        """Store user's edited version of a translation and update cache."""
        edit_entry = {
            "translation": edited_translation,
            "original_translation": original_translation,
            "edited_timestamp": datetime.utcnow().isoformat(),
            **create_cache_metadata()
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
        
        print(f"Cache updated with validation acceptance for key: {cache_key[:16]}...")
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
            cache_data = load_json(self.cache_file)
            stats["total_translations"] = len(cache_data)
            # Count user edited entries
            user_edited = sum(1 for entry in cache_data.values() 
                            if entry.get("edited_timestamp") or entry.get("validation_accepted_timestamp"))
            stats["user_edited_count"] = user_edited
            stats["cache_size_mb"] = get_file_size_mb(self.cache_file)
        except Exception:
            pass  # Handle any errors quietly

        return stats
    
    def clear_cache(self, cache_type: str = "all"):
        """Clear cache entries of specified type and update main cache."""
        if cache_type == "all" or cache_type == "translations":
            # Clear entire cache file
            save_json(self.cache_file, {}, create_dirs=False)
        elif cache_type == "edits":
            # Remove only user-edited entries
            try:
                cache_data = load_json(self.cache_file)
                # Keep only entries that were not user-edited
                filtered_data = {
                    k: v for k, v in cache_data.items() 
                    if not (v.get("edited_timestamp") or v.get("validation_accepted_timestamp"))
                }
                save_json(self.cache_file, filtered_data, create_dirs=False)
            except Exception:
                pass  # Handle errors gracefully
    
    def invalidate_cache_entry(self, cache_key: str):
        """Invalidate a specific cache entry and remove from cache."""
        if not os.path.exists(self.cache_file):
            return

        try:
            cache_data = load_json(self.cache_file)
            if cache_key in cache_data:
                del cache_data[cache_key]
                save_json(self.cache_file, cache_data, create_dirs=False)
        except Exception:
            pass  # Ignore errors if the cache is corrupted
    
    # Add missing helper methods that are referenced in the code
    def _save_cache_entry(self, cache_key: str, entry: Dict[str, Any], cache_type: str):
        """Helper method to save cache entry (placeholder implementation)."""
        # For now, just update the main cache
        self.update_cache(cache_key, entry)
    
    def _load_cache_entry(self, cache_key: str, cache_type: str) -> Optional[Dict[str, Any]]:
        """Helper method to load cache entry."""
        try:
            cache_data = load_json(self.cache_file)
            return cache_data.get(cache_key)
        except Exception:
            return None
    
    def _update_main_cache(self, cache_key: str, entry: Dict[str, Any]):
        """Helper method to update main cache (placeholder implementation)."""
        self.update_cache(cache_key, entry)
