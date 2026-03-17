import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io

st.set_page_config(page_title="My Private Flow", layout="wide")
st.title("🎨 Nano Banana Pro: Multi-Gen")

# --- Sidebar Configuration ---
with st.sidebar:
    api_key = st.text_input("Enter Gemini API Key", type="password")
    model_choice = "gemini-3-pro-image-preview" # Nano Banana Pro
    
    aspect_ratio = st.selectbox("Aspect Ratio", 
        ["1:1", "16:9", "9:16", "4:3", "3:4", "2:3", "3:2"])
    
    num_images = st.slider("Number of Images", 1, 4, 4)
    resolution = st.select_slider("Resolution", options=["1K", "2K", "4K"], value="1K")

# --- Main UI ---
prompt = st.text_area("What do you want to see?", placeholder="A futuristic city...")

if st.button("Generate Images"):
    if not api_key:
        st.error("Please enter your API Key in the sidebar.")
    else:
        client = genai.Client(api_key=api_key)
        
        with st.spinner(f"Generating {num_images} images..."):
            try:
                response = client.models.generate_image(
    model=model_choice,
    prompt=prompt,  # Note: generate_image uses 'prompt', not 'contents'
    config=types.GenerateImageConfig(  # Use GenerateImageConfig here
        aspect_ratio=aspect_ratio,
        number_of_images=num_images,  # Note: the parameter name is 'number_of_images'
                        # resolution=resolution # Feature available in specific regions
                    )
                )
                
                # Display results in a grid
                cols = st.columns(2)
                for i, candidate in enumerate(response.candidates):
                    for part in candidate.content.parts:
                        if part.inline_data:
                            img = PIL.Image.open(io.BytesIO(part.inline_data.data))
                            cols[i % 2].image(img, use_container_width=True, caption=f"Variant {i+1}")
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()
st.caption("Using Gemini Ultra Cloud Credits via API.")
