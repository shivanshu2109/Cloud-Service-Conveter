import streamlit as st
import json
import os
from cache_manager import CacheManager

# Page configuration
st.set_page_config(
    page_title="Cloud Converter Cache Download",
    page_icon="📥",
    layout="centered"
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 1.5rem;
        border-radius: 10px;
    }
    .download-section {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
        margin: 2rem 0;
    }
    .stButton > button {
        border-radius: 5px;
        font-weight: bold;
        font-size: 1.2rem;
        padding: 0.5rem 2rem;
    }
    .footer {
        text-align: center;
        color: #6c757d;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>Cloud Converter Cache Download</h1>
    <p>Download the main cache file for sharing or backup</p>
</div>
""", unsafe_allow_html=True)

# Initialize the Cache Manager
cache_manager = CacheManager("cache")  # Using default cache directory

def main():
    # Display cache info
    st.header("Cache Information")
    
    # Check if cache file exists
    if os.path.exists(cache_manager.cache_file):
        try:
            with open(cache_manager.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # Get cache statistics    
            cache_stats = cache_manager.get_cache_stats()
            
            # Display cache stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Translations", cache_stats["total_translations"])
            with col2:
                st.metric("User Edited", cache_stats["user_edited_count"])
            with col3:
                st.metric("Cache Size (MB)", cache_stats["cache_size_mb"])
            
            # Main download section
            st.markdown('<div class="download-section">', unsafe_allow_html=True)
            st.markdown("### Download Main Cache File")
            st.markdown("This will download the main translations cache file: **translations_cache.json**")
            
            # Read cache file for download
            with open(cache_manager.cache_file, 'r', encoding='utf-8') as f:
                cache_content = f.read()
            
            # Download button
            st.download_button(
                label="📥 Download Cache File",
                data=cache_content,
                file_name="translations_cache.json",
                mime="application/json",
                use_container_width=True,
                type="primary",
                help="Download the main cache file containing all translations"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Additional options
            with st.expander("Cache File Details", expanded=False):
                st.markdown(f"**Cache File Location:** `{cache_manager.cache_file}`")
                st.markdown(f"**Number of Cache Entries:** {len(cache_data)}")
                st.markdown("**Cache File Structure:**")
                st.json(next(iter(cache_data.values())) if cache_data else {})
                
        except Exception as e:
            st.error(f"Error accessing cache file: {str(e)}")
    else:
        st.warning("Cache file not found. Please run the main application first to generate cache data.")
        st.markdown(f"Expected cache file location: `{cache_manager.cache_file}`")

    # Footer
    st.markdown('<div class="footer">Cloud Converter Cache Utility</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
