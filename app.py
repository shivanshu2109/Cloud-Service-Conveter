import streamlit as st
import yaml
import json
import os
from llm_handler import get_translation, get_cache_path
from utils import save_yaml, load_yaml

# --- Page Configuration ---
st.set_page_config(page_title="Cloud Configuration Translator", layout="wide")
st.title("☁️ Cloud Configuration Translator")

# --- Input Configuration Section ---
st.header("1. Input Configuration")
source_cloud = st.selectbox("Source Cloud", ["aws", "azure", "gcp"])
target_cloud = st.selectbox("Target Cloud", ["gcp", "azure", "aws"])

uploaded_file = st.file_uploader("Upload your source YAML file:", type=['yaml', 'yml'])

if 'final_output' not in st.session_state:
    st.session_state.final_output = None

# --- Translation Results Section ---
st.header("2. Translation Results")

if st.button("Translate", type="primary"):
    if uploaded_file is not None:
        try:
            input_yaml_str = uploaded_file.getvalue().decode("utf-8")
            source_yaml = yaml.safe_load(input_yaml_str)
            translated_resources = []
            
            with st.spinner("Translating..."):
                for i, resource in enumerate(source_yaml.get("resources", [])):
                    converted_dict = get_translation(resource, source_cloud, target_cloud)
                    
                    with st.expander(f"**{i+1}. {resource.get('id', 'Unknown ID')}** - Comparison"):
                        exp_col1, exp_col2 = st.columns(2)
                        with exp_col1:
                            st.subheader(f"Original {source_cloud.upper()}")
                            st.code(yaml.dump(resource, indent=2, sort_keys=False), language='yaml')
                        with exp_col2:
                            st.subheader(f"Translated {target_cloud.upper()}")
                            if "error" in converted_dict:
                                st.error(converted_dict['error'])
                            else:
                                st.code(yaml.dump(converted_dict, indent=2, sort_keys=False), language='yaml')
                    
                    if "error" not in converted_dict:
                        translated_resources.append(converted_dict)

            st.session_state.final_output = {
                "version": 1,
                "provider": target_cloud,
                "resources": translated_resources
            }
            
            save_yaml(f"output/translated_{target_cloud}.yaml", st.session_state.final_output)
            st.success(f"Translation complete! Results are displayed below. Output YAML has been saved.")

        except yaml.YAMLError as e:
            st.error(f"Invalid YAML format in input file: {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
    else:
        st.warning("Please upload a source YAML file.")

# --- Download Button (Updated for YAML) ---
if st.session_state.final_output:
    st.download_button(
        label="📥 Download Translated YAML",
        data=yaml.dump(st.session_state.final_output, indent=2, sort_keys=False),
        file_name=f"translated_{target_cloud}.yaml",
        mime="text/yaml"
    )

# --- Cache Management Expander ---
st.markdown("---")
with st.expander("⚙️ View & Edit Cache"):
    st.info(f"Editing cache for: **{source_cloud.upper()} to {target_cloud.upper()}**")
    cache_path_to_edit = get_cache_path(source_cloud, target_cloud)

    if os.path.exists(cache_path_to_edit):
        try:
            with open(cache_path_to_edit, 'r') as f:
                cache_content = json.load(f)
            
            edited_cache_str = st.text_area(
                "Cache Content", 
                value=json.dumps(cache_content, indent=2),
                height=400,
                key="cache_editor"
            )

            if st.button("Save Cache"):
                try:
                    new_cache_data = json.loads(edited_cache_str)
                    with open(cache_path_to_edit, 'w') as f:
                        json.dump(new_cache_data, f, indent=2)
                    st.success("Cache saved successfully!")
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("Invalid JSON format. Please correct it before saving.")
        except Exception as e:
            st.error(f"Could not load or display cache: {e}")
    else:
        st.write("No cache file found for this translation direction yet.")