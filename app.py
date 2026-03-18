import streamlit as st
import io
import time
from google import genai
from google.genai import types
import PIL.Image
import cloudinary
import cloudinary.uploader

# --- Page Config ---
st.set_page_config(page_title="Flow Clone", layout="wide")
st.title("🌊 Flow: Multi-Ratio Image Generator")

# --- Load Secrets Safely ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    cloudinary.config(
        cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
        api_key=st.secrets["CLOUDINARY_API_KEY"],
        api_secret=st.secrets["CLOUDINARY_API_SECRET"]
    )
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error("Failed to load secrets. Please check your .streamlit/secrets.toml file.")
    st.stop()

# --- UI Sidebar ---
with st.sidebar:
    st.header("Settings")
    # Gemini 3.1 Flash Image Preview supports the extreme aspect ratios (1:4, 4:1)
    model_choice = st.selectbox(
        "Model", 
        ["gemini-3.1-flash-image-preview", "gemini-2.5-flash-image"],
        index=0
    )
    st.info("Generating 4 images sequentially to respect API limits. Images will be hosted on Cloudinary.")

# --- Main UI ---
prompt = st.text_area("What do you want to create?", placeholder="A cinematic shot of a cyberpunk city, neon lights, raining...")

if st.button("Generate Flow (4 Images)", type="primary", use_container_width=True):
    if not prompt:
        st.warning("Please enter a prompt first.")
    else:
        # The 4 aspect ratios we want to generate
        # Note: 4:1 (Ultra-Wide) is only supported by gemini-3.1-flash-image-preview
        ratios = ["1:1", "16:9", "9:16", "4:1"] 
        
        # Create a 2x2 grid for our images
        col1, col2 = st.columns(2)
        placeholders = [
            col1.empty(), 
            col2.empty(), 
            col1.empty(), 
            col2.empty()
        ]
        
        st.success("Starting generation sequence...")
        
        # Serialize the generation (one at a time)
        for i, ratio in enumerate(ratios):
            with placeholders[i].container():
                st.info(f"⏳ Generating [{ratio}]...")
                
                try:
                    # 1. Call Gemini API
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            image_config=types.ImageConfig(
                                aspect_ratio=ratio,
                                image_size="1K"
                            )
                        )
                    )
                    
                    # 2. Extract Image
                    img = None
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if part.inline_data:
                                img = PIL.Image.open(io.BytesIO(part.inline_data.data))
                                break
                        if img: break
                    
                    if img:
                        # 3. Upload to Cloudinary
                        st.info(f"☁️ Uploading [{ratio}] to Cloudinary...")
                        buf = io.BytesIO()
                        img.save(buf, format='PNG')
                        
                        upload_result = cloudinary.uploader.upload(
                            buf.getvalue(), 
                            folder="flow_clone",
                            tags=["flow_generated", ratio]
                        )
                        
                        secure_url = upload_result.get("secure_url")
                        
                        # 4. Display the Cloudinary hosted image
                        placeholders[i].empty() # Clear the info messages
                        placeholders[i].image(secure_url, caption=f"Aspect Ratio: {ratio}", use_container_width=True)
                        placeholders[i].markdown(f"[View Original on Cloudinary]({secure_url})")
                    else:
                        placeholders[i].error(f"Failed to generate image for {ratio}")
                        
                except Exception as e:
                    placeholders[i].error(f"Error on {ratio}: {e}")
                
                # Small pause between API calls to ensure we don't hit rate limits
                if i < len(ratios) - 1:
                    time.sleep(2)

        st.balloons()
