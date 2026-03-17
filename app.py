import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io
import cloudinary
import cloudinary.uploader
import cloudinary.api
import uuid
import requests

# --- Page Config & Custom CSS ---
st.set_page_config(page_title="Bullseye Media House", layout="wide")

# Bullseye Studio inspired Dark/Neon Theme
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    header { background-color: transparent !important; }
    
    /* Typography & Titles */
    h1, h2, h3 {
        color: #ff6b00 !important; /* Cyber-Orange Accent */
        font-family: 'Arial Black', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    /* Sleek Button Styling */
    .stButton>button {
        background-color: #ff6b00;
        color: #ffffff;
        font-weight: 800;
        border: none;
        border-radius: 4px;
        text-transform: uppercase;
        transition: all 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #ff8533;
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(255, 107, 0, 0.4);
    }
    
    /* Sidebar & Inputs */
    [data-testid="stSidebar"] {
        background-color: #121826;
        border-right: 1px solid #2d3748;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
        background-color: #1a202c;
        color: #ffffff;
        border: 1px solid #4a5568;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Bullseye Media House")
st.caption("Next-Gen Generative Asset Studio")

# --- Configure Cloudinary ---
try:
    cloudinary.config(
        cloud_name=st.secrets.get("CLOUDINARY_CLOUD_NAME", ""),
        api_key=st.secrets.get("CLOUDINARY_API_KEY", ""),
        api_secret=st.secrets.get("CLOUDINARY_API_SECRET", ""),
        secure=True
    )
except Exception:
    pass 

# --- Session State ---
if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

# --- Cloudinary Admin API Fetchers ---
# Cached so it doesn't spam the API on every UI refresh
@st.cache_data(ttl=10)
def get_cloudinary_folders():
    try:
        result = cloudinary.api.root_folders()
        return [f['name'] for f in result.get('folders', [])]
    except Exception:
        return []

@st.cache_data(ttl=5)
def get_images_in_folder(folder_name):
    try:
        result = cloudinary.api.resources(
            type="upload",
            prefix=f"{folder_name}/", # Prefix search gets items in the folder
            max_results=50
        )
        return result.get("resources", [])
    except Exception:
        return []

# --- Helper Functions ---
def get_closest_aspect_ratio(image: PIL.Image.Image) -> str:
    w, h = image.size
    ratio = w / h
    # Ensure this entire line is copied, including the closing brace at the end
    ratios = {"1:1": 1.0, "16:9": 1.777, "9:16": 0.562, "4:3": 1.333, "3:4": 0.75}
    return min(ratios.keys(), key=lambda k: abs(ratios[k] - ratio))
