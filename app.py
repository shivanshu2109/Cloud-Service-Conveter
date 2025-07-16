import streamlit as st
import yaml
import json
import os
from llm_handler import get_translation, get_cache_path
from utils import save_yaml, load_yaml

# --- Load Config ---
with open('config.json', 'r') as f:
    config = json.load(f)
AVAILABLE_MODELS = config.get("available_models", {})

# --- NEW: Helper function to enforce key order ---
def reorder_dict(data: dict) -> dict:
    """Reorders a dictionary to match the desired input structure."""
    if not isinstance(data, dict):
        return data # Return as-is if it's not a dictionary (e.g., an error string)
        
    desired_order = ["id", "service", "resource_type", "region", "quantity", "configuration"]
    # Create a new dictionary with the keys in the correct order
    ordered_data = {key: data.get(key) for key in desired_order if key in data}
    # Add any other keys that might exist but weren't in the desired order
    for key, value in data.items():
        if key not in ordered_data:
            ordered_data[key] = value
    return ordered_data

# --- Helper Function for HTML Report ---
def generate_html_report(comparison_data, source_cloud, target_cloud):
    html = f"""
    <html>
    <head>
        <title>Cloud Translation Comparison</title>
        <style>
            body {{ font-family: sans-serif; margin: 2em; background-color: #f0f2f6; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 2em; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; vertical-align: top; }}
            th {{ background-color: #e9ecef; color: #495057; }}
            pre {{ white-space: pre-wrap; word-wrap: break-word; background-color: #fff; padding: 10px; border-radius: 5px; border: 1px solid #eee; }}
            h1, h2 {{ color: #333; border-bottom: 2px solid #ccc; padding-bottom: 10px;}}
        </style>
    </head>
    <body>
        <h1>Translation Comparison: {source_cloud.upper()} to {target_cloud.upper()}</h1>
    """

    for resource_id, data in comparison_data.items():
        html += f"<h2>Resource: {resource_id}</h2><table><tr>"
        html += f"<th>Original {source_cloud.upper()}</th>"
        
        models = list(data['translations'].keys())
        for model_name in models:
            html += f"<th>{model_name}</th>"
        html += "</tr><tr>"

        # Original resource column
        ordered_original = reorder_dict(data['original'])
        html += f"<td><pre>{yaml.dump(ordered_original, indent=2, sort_keys=False)}</pre></td>"

        # Translated resource columns
        for model_name in models:
            ordered_translation = reorder_dict(data['translations'][model_name])
            html += f"<td><pre>{yaml.dump(ordered_translation, indent=2, sort_keys=False)}</pre></td>"
        
        html += "</tr></table>"

    html += "</body></html>"
    return html

# --- Page Configuration ---
st.set_page_config(page_title="Cloud Configuration Translator", layout="wide")
st.title("☁️ Cloud Configuration Translator")

# --- Input Configuration Section ---
st.header("1. Input Configuration")
c1, c2, c3 = st.columns(3)
with c1:
    source_cloud = st.selectbox("Source Cloud", ["aws", "azure", "gcp"])
with c2:
    target_cloud = st.selectbox("Target Cloud", ["gcp", "azure", "aws"])
with c3:
    model_options = ["All Models"] + list(AVAILABLE_MODELS.keys())
    selected_option = st.selectbox("Select Model for Translation", model_options)

uploaded_file = st.file_uploader("Upload your source YAML file:", type=['yaml', 'yml'])

# --- Session State Initialization ---
if 'translation_results' not in st.session_state:
    st.session_state.translation_results = None
if 'comparison_mode' not in st.session_state:
    st.session_state.comparison_mode = False

# --- Translation Logic ---
if st.button("Translate", type="primary"):
    if uploaded_file is not None:
        st.session_state.translation_results = None
        
        input_yaml_str = uploaded_file.getvalue().decode("utf-8")
        source_yaml = yaml.safe_load(input_yaml_str)
        
        if selected_option == "All Models":
            st.session_state.comparison_mode = True
            comparison_data = {}
            with st.spinner("Running comparison across all models..."):
                for resource in source_yaml.get("resources", []):
                    res_id = resource.get('id', 'unknown')
                    comparison_data[res_id] = {'original': resource, 'translations': {}}
                    for model_name, model_info in AVAILABLE_MODELS.items():
                        st.write(f"  - Translating '{res_id}' using '{model_name}'...")
                        translation = get_translation(resource, source_cloud, target_cloud, model_info)
                        comparison_data[res_id]['translations'][model_name] = translation
            st.session_state.translation_results = comparison_data
            st.success("Comparison complete!")
        else: # Single model selected
            st.session_state.comparison_mode = False
            model_info_to_use = AVAILABLE_MODELS[selected_option]
            translated_resources = []
            with st.spinner(f"Translating using {selected_option}..."):
                for resource in source_yaml.get("resources", []):
                    translation = get_translation(resource, source_cloud, target_cloud, model_info_to_use)
                    translated_resources.append({'original': resource, 'translation': translation})
            st.session_state.translation_results = translated_resources
            st.success("Translation complete!")
    else:
        st.warning("Please upload a source YAML file.")

# --- Display Results Section ---
st.header("2. Translation Results")

if st.session_state.translation_results:
    if st.session_state.comparison_mode:
        for resource_id, data in st.session_state.translation_results.items():
            with st.expander(f"**Resource: {resource_id}**"):
                num_models = len(data['translations'])
                cols = st.columns(num_models + 1)
                
                with cols[0]:
                    st.subheader(f"Original {source_cloud.upper()}")
                    ordered_original = reorder_dict(data['original'])
                    st.code(yaml.dump(ordered_original, indent=2, sort_keys=False), language='yaml')

                for i, (model_name, translation) in enumerate(data['translations'].items()):
                    with cols[i+1]:
                        st.subheader(model_name)
                        ordered_translation = reorder_dict(translation)
                        st.code(yaml.dump(ordered_translation, indent=2, sort_keys=False), language='yaml')
        
        st.download_button(
            "Download Full Comparison Report (HTML)", 
            generate_html_report(st.session_state.translation_results, source_cloud, target_cloud), 
            "comparison_report.html", 
            "text/html"
        )
    else:
        for item in st.session_state.translation_results:
            with st.expander(f"**Resource: {item['original'].get('id', 'Unknown ID')}**"):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(f"Original {source_cloud.upper()}")
                    ordered_original = reorder_dict(item['original'])
                    st.code(yaml.dump(ordered_original, indent=2, sort_keys=False), language='yaml')
                with col2:
                    st.subheader(f"Translated {target_cloud.upper()}")
                    ordered_translation = reorder_dict(item['translation'])
                    st.code(yaml.dump(ordered_translation, indent=2, sort_keys=False), language='yaml')
        
        final_yaml_output = {
            "version": 1, 
            "provider": target_cloud, 
            "resources": [reorder_dict(item['translation']) for item in st.session_state.translation_results if 'error' not in item['translation']]
        }
        st.download_button(
            "Download Translated YAML", 
            yaml.dump(final_yaml_output, indent=2, sort_keys=False), 
            f"translated_{target_cloud}.yaml", 
            "text/yaml"
        )
else:
    st.info("Click 'Translate' to see results.")

# --- Cache Management Expander ---
st.markdown("---")
with st.expander("⚙️ View & Edit Cache"):
    model_names_for_cache = list(AVAILABLE_MODELS.keys())
    cache_model_name = st.selectbox("Select model cache to view/edit", model_names_for_cache)
    model_info_for_cache = AVAILABLE_MODELS[cache_model_name]
    
    st.info(f"Editing cache for: **{source_cloud.upper()} to {target_cloud.upper()}** using model **{cache_model_name}**")
    cache_path_to_edit = get_cache_path(source_cloud, target_cloud, model_info_for_cache['arn'])

    if os.path.exists(cache_path_to_edit):
        with open(cache_path_to_edit, 'r') as f:
            cache_content = json.load(f)
        edited_cache_str = st.text_area("Cache Content", json.dumps(cache_content, indent=2), height=400, key=f"cache_{cache_model_name}")
        if st.button("Save Cache"):
            try:
                new_cache_data = json.loads(edited_cache_str)
                with open(cache_path_to_edit, 'w') as f:
                    json.dump(new_cache_data, f, indent=2)
                st.success("Cache saved!")
                st.rerun()
            except json.JSONDecodeError:
                st.error("Invalid JSON format. Please correct it before saving.")
    else:
        st.write("No cache file found for this translation direction and model yet.")
