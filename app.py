import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io

st.set_page_config(page_title="My Private Flow", layout="wide")
st.title("🎨 Image Generator (Imagen 3)")

# --- Sidebar Configuration ---
with st.sidebar:
    # Allows falling back to manual input if secrets aren't set up right locally
    api_key_input = st.text_input("Enter Gemini API Key (or leave blank to use Secrets)", type="password")
    
    # The correct model string for image generation in the API
    model_choice = "imagen-3.0-generate-001" 
    
    # Supported aspect ratios for Imagen 3
    aspect_ratio = st.selectbox("Aspect Ratio", 
        ["1:1", "16:9", "9:16", "4:3", "3:4"])
    
    num_images = st.slider("Number of Images", 1, 4, 4)

# --- Main UI ---
prompt = st.text_area("What do you want to see?", placeholder="A futuristic city...")

if st.button("Generate Images"):
    # Prioritize manual input, fallback to Streamlit secrets
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    if not api_key:
        st.error("Please enter your API Key in the sidebar or add it to Streamlit secrets.")
    else:
        client = genai.Client(api_key=api_key)
        
        with st.spinner(f"Generating {num_images} images..."):
            try:
                # Use generate_images instead of generate_content
                response = client.models.generate_images(
                    model=model_choice,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=num_images,
                        aspect_ratio=aspect_ratio,
                        output_mime_type="image/jpeg",
                        # person_generation="ALLOW_ADULT" # Optional: Un-comment if you need to allow people generation based on your API tier
                    )
                )
                
                # Display results in a grid
                cols = st.columns(2)
                for i, generated_image in enumerate(response.generated_images):
                    # The response object structure is different for generate_images
                    img = PIL.Image.open(io.BytesIO(generated_image.image.image_bytes))
                    cols[i % 2].image(img, use_container_width=True, caption=f"Variant {i+1}")
            except Exception as e:
                st.error(f"Error: {e}")

st.divider()
st.caption("Powered by Google GenAI.")
