import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io

st.set_page_config(page_title="My Private Flow", layout="wide")
st.title("🎨 Multi-Gen Image Studio")

# --- Session State ---
# This ensures images stay on screen when buttons are clicked
if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

# --- Sidebar Configuration ---
with st.sidebar:
    api_key_input = st.text_input("Enter Gemini API Key (or leave blank for Secrets)", type="password")
    
    model_choice = st.selectbox(
        "Select Model",
        [
            "gemini-3-flash-image",        # Nano Banana 2
            "imagen-4.0-generate-001",     # Imagen 4 GA
            "imagen-4.0-fast-generate-001" # Imagen 4 Fast
        ],
        help="Gemini 3 Flash Image is the API equivalent of Nano Banana 2."
    )
    
    image_quality = st.selectbox(
        "Image Quality", 
        ["1K", "2K", "4K"], 
        help="Note: Imagen 4 natively supports up to 2K. Gemini 3 models support up to 4K."
    )
    
    aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "16:9", "9:16", "4:3", "3:4"])
    num_images = st.slider("Number of Images", 1, 4, 4)

# --- Main UI ---
prompt = st.text_area("What do you want to see?", placeholder="A futuristic city...")

if st.button("Generate Images"):
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    if not api_key:
        st.error("Please enter your API Key in the sidebar or add it to Streamlit secrets.")
    elif not prompt:
        st.warning("Please enter a prompt.")
    else:
        client = genai.Client(api_key=api_key)
        st.session_state.generated_images = [] # Clear previous generation
        
        with st.spinner(f"Generating {num_images} images using {model_choice}..."):
            try:
                # --- BRANCH 1: IMAGEN MODELS ---
                if "imagen" in model_choice:
                    response = client.models.generate_images(
                        model=model_choice,
                        prompt=prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=num_images,
                            aspect_ratio=aspect_ratio,
                            output_mime_type="image/jpeg",
                            # Note: Actual API size parameters depend on your Cloud/Vertex config
                        )
                    )
                    for img_data in response.generated_images:
                        st.session_state.generated_images.append(img_data.image.image_bytes)

                # --- BRANCH 2: GEMINI MODELS ---
                elif "gemini" in model_choice:
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            candidate_count=num_images,
                            response_modalities=["IMAGE"],
                            image_config=types.ImageConfig(
                                aspect_ratio=aspect_ratio
                            )
                        )
                    )
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if part.inline_data:
                                st.session_state.generated_images.append(part.inline_data.data)
                                
            except Exception as e:
                st.error(f"Error: {e}")

# --- Display Results & Action Buttons ---
if st.session_state.generated_images:
    cols = st.columns(2)
    for i, img_bytes in enumerate(st.session_state.generated_images):
        with cols[i % 2]:
            # Display Image
            img = PIL.Image.open(io.BytesIO(img_bytes))
            st.image(img, use_container_width=True, caption=f"Variant {i+1}")
            
            # Create a row for buttons under the image
            btn_cols = st.columns(2)
            
            # Download Button
            with btn_cols[0]:
                st.download_button(
                    label="⬇️ Download",
                    data=img_bytes,
                    file_name=f"flow_generation_{i+1}.jpeg",
                    mime="image/jpeg",
                    use_container_width=True,
                    key=f"dl_{i}"
                )
            
            # Upscale Button
            with btn_cols[1]:
                if image_quality != "4K":
                    if st.button("✨ Upscale to 4K", use_container_width=True, key=f"up_{i}"):
                        st.info("Upscale logic would execute here!")

st.divider()
st.caption("Powered by Google GenAI.")
