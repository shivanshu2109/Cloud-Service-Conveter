import streamlit as st
import yaml
import json
import os
import boto3
import time
from io import StringIO
from llm_handler import get_translation, get_cache_path, save_yaml, load_yaml
from cache_manager import CacheManager
from validator import ValidationHandler

# --- Load Config & Initialize Services ---
with open('config.json', 'r') as f:
    config = json.load(f)
AVAILABLE_MODELS = config.get("available_models", {})

if 'bedrock_client' not in st.session_state:
    try:
        st.session_state.bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=config.get("aws_region"))
    except Exception as e:
        st.error(f"Failed to initialize Bedrock client: {e}")
        st.session_state.bedrock_client = None

if 'validator' not in st.session_state:
    st.session_state.validator = ValidationHandler(st.session_state.bedrock_client, config)

# Initialize the Cache Manager
cache_manager = CacheManager(config.get("cache_dir", "cache"))

# --- Helper function to enforce key order ---
def reorder_dict(data: dict) -> dict:
    if not isinstance(data, dict): return data
    desired_order = ["id", "service", "resource_type", "region", "quantity", "configuration"]
    ordered_data = {key: data.get(key) for key in desired_order if key in data}
    for key, value in data.items():
        if key not in ordered_data: ordered_data[key] = value
    return ordered_data

# --- Function to detect changes between two dictionaries ---
def detect_changes(original: dict, modified: dict, path="") -> dict:
    """Detect changes between two dictionaries and return change information."""
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

# --- Function to create highlighted changes using Streamlit components ---
def display_highlighted_changes(original_data: dict, modified_data: dict, changes: dict):
    """Display changes using Streamlit's native components with clear highlighting."""
    
    # Show a simple comparison with highlighted changed fields
    changed_fields = set()
    for change in changes.get("modified", []):
        changed_fields.add(change["path"])
    for change in changes.get("added", []):
        changed_fields.add(change["path"])
    for change in changes.get("removed", []):
        changed_fields.add(change["path"])
    
    if not changed_fields:
        st.warning("No changes detected between before and after validation.")
        return
    
    # Create highlighted YAML display
    original_yaml = yaml.dump(reorder_dict(original_data), indent=2, sort_keys=False)
    modified_yaml = yaml.dump(reorder_dict(modified_data), indent=2, sort_keys=False)
    
    # Show field-by-field changes
    st.markdown("### 🔍 Field-Level Changes:")
    
    for change in changes.get("modified", []):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.markdown(f"**📝 Field:** `{change['path']}`")
        with col2:
            st.markdown(f"**🔴 Before:** `{change['old_value']}`")
        with col3:
            st.markdown(f"**🟢 After:** `{change['new_value']}`")
        st.markdown("---")
    
    for change in changes.get("added", []):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**📝 Field:** `{change['path']}`")
        with col2:
            st.markdown(f"**🔵 Added:** `{change['value']}`")
        st.markdown("---")
    
    for change in changes.get("removed", []):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**📝 Field:** `{change['path']}`")
        with col2:
            st.markdown(f"**🟠 Removed:** `{change['value']}`")
        st.markdown("---")
    
    return original_yaml, modified_yaml

# --- Function to create highlighted YAML for suggestions ---
def create_diff_highlighted_yaml(yaml_data: dict, changes: dict) -> str:
    """Create highlighted YAML showing what will change."""
    import html
    
    yaml_str = yaml.dump(reorder_dict(yaml_data), indent=2, sort_keys=False)
    lines = yaml_str.split('\n')
    highlighted_lines = []
    
    # Create sets for quick lookup
    modified_fields = set()
    added_fields = set()
    removed_fields = set()
    
    for change in changes.get("modified", []):
        modified_fields.add(change["path"].split('.')[-1])  # Get last part of path
    for change in changes.get("added", []):
        added_fields.add(change["path"].split('.')[-1])
    for change in changes.get("removed", []):
        removed_fields.add(change["path"].split('.')[-1])
    
    # Process each line
    for line in lines:
        if not line.strip():
            highlighted_lines.append(html.escape(line))
            continue
        
        line_highlighted = False
        escaped_line = html.escape(line)
        
        # Check if line contains a field that will change
        if ":" in line:
            # Extract field name (everything before the colon, stripped)
            field_name = line.split(":")[0].strip()
            
            if field_name in modified_fields:
                # Yellow/orange background for modified fields
                highlighted_lines.append(f'<span style="background-color: #ffa726; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{escaped_line}</span>')
                line_highlighted = True
            elif field_name in added_fields:
                # Green background for added fields
                highlighted_lines.append(f'<span style="background-color: #66bb6a; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{escaped_line}</span>')
                line_highlighted = True
            elif field_name in removed_fields:
                # Red background for removed fields
                highlighted_lines.append(f'<span style="background-color: #ef5350; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold;">{escaped_line}</span>')
                line_highlighted = True
        
        if not line_highlighted:
            highlighted_lines.append(escaped_line)
    
    # Wrap in a styled container
    highlighted_content = '\n'.join(highlighted_lines)
    return f'''
    <div style="
        background-color: #1e1e1e; 
        color: #d4d4d4; 
        padding: 1rem; 
        border-radius: 8px; 
        font-family: 'Courier New', monospace; 
        font-size: 14px; 
        line-height: 1.4; 
        white-space: pre-wrap; 
        overflow-x: auto;
        border: 1px solid #444;
    ">
{highlighted_content}
    </div>
    '''

# --- Callback function to handle accepting a suggestion ---
def accept_suggestion_callback(item_index, correction, source_cloud, target_cloud, model_info):
    """Saves the corrected translation to the cache AND updates the UI state."""
    # Get the specific item from session state
    item = st.session_state.translation_run[item_index]
    resource = item['original']
    original_translation = item['translated'].copy()  # Store the original before changes

    # 1. Use the existing cache key from the item (generated during original translation)
    cache_key = item.get('cache_key')
    if not cache_key:
        # Fallback: generate cache key if not found
        cache_key = cache_manager._generate_cache_key(
            resource, 
            st.session_state.input_content,  # Use the original input content
            source_cloud, 
            target_cloud, 
            model_info['arn']
        )
    
    # Update the cache with validation acceptance
    cache_manager.store_validation_acceptance(cache_key, correction, item['translated'])

    # 2. Update the session state to reflect the change in the UI
    st.session_state.translation_run[item_index]['translated'] = correction
    # Clear the suggestion and issues, and mark as corrected
    st.session_state.translation_run[item_index]['validation']['suggested_correction'] = None
    st.session_state.translation_run[item_index]['validation']['issues'] = []
    st.session_state.translation_run[item_index]['validation']['confidence_score'] = 100
    # Mark changes as applied and store the original for comparison
    st.session_state.translation_run[item_index]['validation']['changes_applied'] = True
    st.session_state.translation_run[item_index]['validation']['original_translation'] = original_translation

    st.toast(f"✅ Validation accepted! Cache updated for '{resource.get('id')}'!")
    st.success(f"Translation corrected and cached for future use!")

# --- Initialize Enhanced Session State for New UI Features ---
if 'input_content' not in st.session_state:
    st.session_state.input_content = ""
if 'output_content' not in st.session_state:
    st.session_state.output_content = ""
if 'ai_suggestion' not in st.session_state:
    st.session_state.ai_suggestion = ""
if 'ai_validated' not in st.session_state:
    st.session_state.ai_validated = False
if 'ai_loading' not in st.session_state:
    st.session_state.ai_loading = False
if 'current_file' not in st.session_state:
    st.session_state.current_file = None
if 'manual_input_mode' not in st.session_state:
    st.session_state.manual_input_mode = False

# --- Page Configuration ---
st.set_page_config(page_title="Cloud Configuration Translator", layout="wide")

# Custom CSS for enhanced styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 2rem;
        border-radius: 10px;
    }
    .ai-suggestion-box {
        background-color: #f0f8ff;
        border: 2px solid #4682b4;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .validation-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .validation-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .editor-panel {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stButton > button {
        border-radius: 5px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>Cloud Configuration Translator & Validator</h1>
    <p>AI-Powered Configuration File Editor</p>
</div>
""", unsafe_allow_html=True)

# --- Input Configuration Section ---
st.header("1. Input Configuration")
c1, c2, c3 = st.columns(3)
with c1:
    source_cloud = st.selectbox("Source Cloud", ["aws", "azure", "gcp"])
with c2:
    target_cloud = st.selectbox("Target Cloud", ["gcp", "azure", "aws"])
with c3:
    model_options = list(AVAILABLE_MODELS.keys())
    selected_option = st.selectbox("Select Model for Translation", model_options)

# Input mode selection
input_mode = st.radio(
    "Choose input method:",
    ["Upload File", "Manual Input"],
    horizontal=True
)

if input_mode == "Upload File":
    uploaded_file = st.file_uploader("Upload your source YAML file:", type=['yaml', 'yml'])
    if uploaded_file is not None:
        if uploaded_file != st.session_state.current_file:
            st.session_state.current_file = uploaded_file
            content = StringIO(uploaded_file.getvalue().decode("utf-8")).read()
            st.session_state.input_content = content
            st.success(f"Loaded: {uploaded_file.name}")
else:
    st.session_state.manual_input_mode = True
    uploaded_file = None

# --- Cache Management Section ---
with st.expander("Cache Management", expanded=False):
    cache_stats = cache_manager.get_cache_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Translations", cache_stats["total_translations"])
    with col2:
        st.metric("User Edited", cache_stats["user_edited_count"])
    with col3:
        st.metric("Cache Size (MB)", cache_stats["cache_size_mb"])
    
    st.markdown("### Cache Operations")
    cache_col1, cache_col2, cache_col3 = st.columns(3)
    
    with cache_col1:
        if st.button("Clear All Cache"):
            cache_manager.clear_cache("all")
            st.success("All cache cleared!")
            st.rerun()
    
    with cache_col2:
        if st.button("Clear Translation Cache"):
            cache_manager.clear_cache("translations")
            st.success("Translation cache cleared!")
            st.rerun()
    
    with cache_col3:
        if st.button("Clear User Edits"):
            cache_manager.clear_cache("edits")
            st.success("User edits cleared!")
            st.rerun()

# --- Session State Management ---
if 'translation_run' not in st.session_state:
    st.session_state.translation_run = []

if st.button("Translate", type="primary"):
    st.session_state.translation_run = []  # Clear previous results
    if uploaded_file is not None:
        input_yaml_str = uploaded_file.getvalue().decode("utf-8")
        source_yaml = yaml.safe_load(input_yaml_str)
        model_info_to_use = AVAILABLE_MODELS[selected_option]
        
        with st.spinner(f"Translating and validating using {selected_option}..."):
            cache_hits = 0
            cache_misses = 0
            
            for resource in source_yaml.get("resources", []):
                # Check cache first
                cache_hit, cached_result, cache_key = cache_manager.check_cache(
                    resource, input_yaml_str, source_cloud, target_cloud, model_info_to_use['arn']
                )
                
                if cache_hit:
                    translated_resource = cached_result
                    cache_hits += 1
                    cache_manager.update_access_count(cache_key)
                else:
                    # Cache miss - perform translation
                    translated_resource = get_translation(resource, source_cloud, target_cloud, model_info_to_use)
                    cache_misses += 1
                    
                    # Store in cache if translation was successful
                    if isinstance(translated_resource, dict) and "error" not in translated_resource:
                        cache_manager.store_translation(
                            cache_key, translated_resource, resource,
                            source_cloud, target_cloud, model_info_to_use['arn']
                        )
                
                # Store all results in session state to persist them (without validation initially)
                st.session_state.translation_run.append({
                    "original": resource,
                    "translated": translated_resource,
                    "validation": {"confidence_score": 0, "issues": [], "validated": False},  # Empty validation initially
                    "cache_key": cache_key,
                    "from_cache": cache_hit
                })
        
        # Display cache statistics
        if cache_hits > 0 or cache_misses > 0:
            st.info(f"Cache hits: {cache_hits} | Cache misses: {cache_misses}")
        st.success("Translation complete! Click 'Validate' to check the results.")
    else:
        st.warning("Please upload a source YAML file.")

# --- Display Results Section (reads from session state) ---
if st.session_state.translation_run:
    st.header("2. Translation & Validation Results")
    for i, item in enumerate(st.session_state.translation_run):
        resource = item["original"]
        translated_resource = item["translated"]
        validation_report = item["validation"]
        model_info = AVAILABLE_MODELS[selected_option]
        cache_indicator = "From Cache" if item.get("from_cache", False) else "New Translation"

        with st.expander(f"**{i+1}. {resource.get('id', 'Unknown ID')}** - {cache_indicator}", expanded=True):
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                st.subheader(f"Original {source_cloud.upper()}")
                st.code(yaml.dump(reorder_dict(resource), indent=2, sort_keys=False), language='yaml')
            with exp_col2:
                st.subheader(f"Current Translation {target_cloud.upper()}")
                st.code(yaml.dump(reorder_dict(translated_resource), indent=2, sort_keys=False), language='yaml')

            # --- Edit Translation Output Section ---
            # Initialize edit state for this resource
            edit_state_key = f"edit_mode_{i}"
            if edit_state_key not in st.session_state:
                st.session_state[edit_state_key] = False

            # Toggle edit mode
            if st.button("Edit Translation Output", key=f"edit_output_{i}"):
                st.session_state[edit_state_key] = not st.session_state[edit_state_key]
                st.rerun()

            # Show edit interface if in edit mode
            if st.session_state[edit_state_key]:
                st.markdown(f"**Editing Translation for {resource.get('id')}**")
                current_yaml = yaml.dump(reorder_dict(translated_resource), indent=2, sort_keys=False)
                edited_yaml = st.text_area(
                    "Edit the translated YAML:",
                    value=current_yaml,
                    height=200,
                    key=f"edit_area_{i}"
                )
                # Buttons for saving edits and reverting
                edit_col1, edit_col2, edit_col3 = st.columns(3)

                with edit_col1:
                    if st.button("Save Edits", key=f"save_edit_{i}"):
                        try:
                            # Parse the edited YAML
                            edited_translation = yaml.safe_load(edited_yaml)

                            # Update the cache with user's edit
                            cache_key = item.get('cache_key')
                            if cache_key:
                                cache_manager.store_user_edit(cache_key, edited_translation, translated_resource)

                            # Update session state
                            st.session_state.translation_run[i]['translated'] = edited_translation
                            st.session_state[edit_state_key] = False  # Close edit mode

                            st.success(f"Edits saved for '{resource.get('id')}'!")
                            st.rerun()

                        except yaml.YAMLError as e:
                            st.error(f"Invalid YAML syntax: {e}")
                        except Exception as e:
                            st.error(f"Error saving edits: {e}")

                with edit_col2:
                    if st.button("Revert to Original", key=f"revert_{i}"):
                        # Reset to the original cached translation
                        cache_key = item.get('cache_key')
                        if cache_key:
                            # Check if there's an original translation in cache
                            cache_entry = cache_manager._load_cache_entry(cache_key, "translations")
                            if cache_entry:
                                st.session_state.translation_run[i]['translated'] = cache_entry['translation']
                                st.session_state[edit_state_key] = False  # Close edit mode
                                st.success(f"Reverted to original translation for '{resource.get('id')}'!")
                                st.rerun()

                with edit_col3:
                    if st.button("Cancel Edit", key=f"cancel_edit_{i}"):
                        st.session_state[edit_state_key] = False  # Close edit mode without saving
                        st.rerun()

            # --- Validation Section ---
            if not validation_report.get('validated', False):
                st.markdown("### Validation")
                if st.button("Validate Translation", key=f"validate_{i}", type="secondary"):
                    with st.spinner(f"Validating translation with {selected_option}..."):
                        import time
                        start_time = time.time()
                        
                        try:
                            # Call validation using the config's validation prompt template
                            validation_report = st.session_state.validator.validate_with_llm(
                                resource, translated_resource, source_cloud, target_cloud, model_info
                            )
                            
                            validation_time = time.time() - start_time
                            st.info(f"Validation completed in {validation_time:.2f} seconds")
                            
                            # Handle validation errors
                            if "error" in validation_report:
                                st.error(f"Validation failed: {validation_report['error']}")
                                validation_report = {
                                    "confidence_score": 0,
                                    "issues": [validation_report['error']],
                                    "validated": True,
                                    "suggested_correction": None
                                }
                            else:
                                validation_report['validated'] = True
                                st.success("Validation completed!")
                            
                            st.session_state.translation_run[i]['validation'] = validation_report
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Validation error: {str(e)}")
                            validation_report = {
                                "confidence_score": 0,
                                "issues": [f"Validation system error: {str(e)}"],
                                "validated": True,
                                "suggested_correction": None
                            }
                            st.session_state.translation_run[i]['validation'] = validation_report
            else:
                st.markdown("### Validation Results")
                
                # Display confidence score with color coding
                confidence = validation_report.get('confidence_score', 0)
                if confidence >= 90:
                    st.success(f"**Confidence Score: {confidence}%** - Excellent translation!")
                elif confidence >= 70:
                    st.warning(f"**Confidence Score: {confidence}%** - Good translation with minor issues")
                elif confidence >= 50:
                    st.warning(f"**Confidence Score: {confidence}%** - Acceptable translation with notable issues")
                else:
                    st.error(f"**Confidence Score: {confidence}%** - Poor translation requiring corrections")

            # Show validation results if available
            if validation_report.get('validated', False):
                issues = validation_report.get('issues', [])
                if issues:
                    st.subheader("Validation Issues Found:")
                    for idx, issue in enumerate(issues, 1):
                        if "ERROR" in issue.upper():
                            st.error(f"**{idx}.** {issue}")
                        elif "WARNING" in issue.upper():
                            st.warning(f"**{idx}.** {issue}")
                        else:
                            st.info(f"**{idx}.** {issue}")
                else:
                    st.success("No validation issues found!")

            # Show suggested correction if available
            if validation_report.get('suggested_correction'):
                st.subheader("AI Suggested Correction:")
                st.info("The AI has suggested improvements to the translation:")
                
                # Detect what will change
                suggested_correction = validation_report['suggested_correction']
                preview_changes = detect_changes(translated_resource, suggested_correction)
                
                # Show summary of what will change
                if preview_changes['modified'] or preview_changes['added'] or preview_changes['removed']:
                    change_preview = []
                    if preview_changes['modified']:
                        change_preview.append(f"🔄 **{len(preview_changes['modified'])} Modified**")
                    if preview_changes['added']:
                        change_preview.append(f"➕ **{len(preview_changes['added'])} Added**")
                    if preview_changes['removed']:
                        change_preview.append(f"➖ **{len(preview_changes['removed'])} Removed**")
                    
                    st.markdown("**Changes Preview:** " + " | ".join(change_preview))
                
                # Show side-by-side comparison with highlighting
                diff_col1, diff_col2 = st.columns(2)
                with diff_col1:
                    st.markdown("**Current Translation:**")
                    st.code(yaml.dump(reorder_dict(translated_resource), indent=2, sort_keys=False), language='yaml')
                
                with diff_col2:
                    st.markdown("**Suggested Changes:**")
                    # Create highlighted version of suggested changes
                    highlighted_yaml = create_diff_highlighted_yaml(suggested_correction, preview_changes)
                    st.markdown(highlighted_yaml, unsafe_allow_html=True)

                # Use the callback to handle the button click
                col1, col2 = st.columns(2)
                with col1:
                    st.button(
                        "Accept Suggestion & Update Cache", 
                        key=f"accept_{i}",
                        on_click=accept_suggestion_callback,
                        type="primary",
                        # Pass the item's index and other necessary info
                        args=(i, validation_report['suggested_correction'], source_cloud, target_cloud, model_info)
                    )
                with col2:
                    if st.button("Re-validate", key=f"revalidate_{i}"):
                        # Reset validation to allow re-validation
                        st.session_state.translation_run[i]['validation'] = {"confidence_score": 0, "issues": [], "validated": False}
                        st.rerun()
            
            # Show validation changes if suggestion was accepted
            if validation_report.get('changes_applied'):
                st.subheader("✅ Validation Changes Applied")
                st.success("The following changes were made based on AI validation:")
                
                # Detect changes between before and after
                original_translation = validation_report.get('original_translation', translated_resource)
                changes = detect_changes(original_translation, translated_resource)
                
                
                # Show summary of changes
                change_summary = []
                if changes['modified']:
                    change_summary.append(f"**Modified:** {len(changes['modified'])} field(s)")
                if changes['added']:
                    change_summary.append(f"**Added:** {len(changes['added'])} field(s)")
                if changes['removed']:
                    change_summary.append(f"**Removed:** {len(changes['removed'])} field(s)")
                
                if change_summary:
                    st.info(" | ".join(change_summary))
                else:
                    st.warning("No changes detected - this might be the issue!")
                
                # Display field-level changes using native Streamlit components
                display_highlighted_changes(original_translation, translated_resource, changes)
                
                # Show full YAML comparison
                st.markdown("### 📄 Full Configuration Comparison:")
                yaml_col1, yaml_col2 = st.columns(2)
                with yaml_col1:
                    st.markdown("**🔴 Before Validation:**")
                    st.code(yaml.dump(reorder_dict(original_translation), indent=2, sort_keys=False), language='yaml')
                    
                with yaml_col2:
                    st.markdown("**🟢 After Validation:**")
                    st.code(yaml.dump(reorder_dict(translated_resource), indent=2, sort_keys=False), language='yaml')
                
                # Show detailed change list
                if changes['modified'] or changes['added'] or changes['removed']:
                    with st.expander("View Detailed Changes", expanded=False):
                        if changes['modified']:
                            st.markdown("**🔄 Modified Fields:**")
                            for change in changes['modified']:
                                st.markdown(f"- **{change['path']}**: `{change['old_value']}` → `{change['new_value']}`")
                        
                        if changes['added']:
                            st.markdown("**➕ Added Fields:**")
                            for change in changes['added']:
                                st.markdown(f"- **{change['path']}**: `{change['value']}`")
                        
                        if changes['removed']:
                            st.markdown("**➖ Removed Fields:**")
                            for change in changes['removed']:
                                st.markdown(f"- **{change['path']}**: `{change['value']}`")

            st.markdown("---")

    # --- Download Translated YAML Section ---
    st.header("3. Download Translated Configuration")
    
    # Create the complete translated YAML structure matching input format
    translated_yaml_structure = {
        "version": 1,
        "provider": target_cloud,
        "resources": []
    }
    
    # Add all translated resources to the structure
    for item in st.session_state.translation_run:
        translated_yaml_structure["resources"].append(reorder_dict(item["translated"]))
    
    # Generate YAML string
    translated_yaml_str = yaml.dump(translated_yaml_structure, indent=2, sort_keys=False)
    
    # Display preview
    with st.expander("Preview Translated YAML", expanded=False):
        st.code(translated_yaml_str, language='yaml')
    
    # Download buttons side by side
    download_col1, download_col2 = st.columns(2)
    
    with download_col1:
        st.download_button(
            label="Download Translated YAML File",
            data=translated_yaml_str,
            file_name=f"translated_{source_cloud}_to_{target_cloud}.yaml",
            mime="application/x-yaml",
            type="primary",
            use_container_width=True
        )
    
    with download_col2:
        # Download Cache Button
        try:
            with open(cache_manager.cache_file, 'r', encoding='utf-8') as f:
                cache_content = f.read()
            
            st.download_button(
                label="📥 Download Cache File",
                data=cache_content,
                file_name="translations_cache.json",
                mime="application/json",
                type="secondary",
                use_container_width=True,
                help="Download the main cache file containing all translations"
            )
        except Exception as e:
            st.error(f"Could not read cache file: {e}")
