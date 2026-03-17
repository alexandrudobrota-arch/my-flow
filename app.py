import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io

st.set_page_config(page_title="My Private Flow", layout="wide")
st.title("🎨 Multi-Gen Image Studio")

# --- Sidebar Configuration ---
with st.sidebar:
    api_key_input = st.text_input("Enter Gemini API Key (or leave blank for Secrets)", type="password")
    
    # Let the user choose between the model families
    model_choice = st.selectbox(
        "Select Model",
        [
            "gemini-3.1-flash-image-preview", # Nano Banana Pro equivalent
            "gemini-2.5-flash-image",         # Nano Banana 2 equivalent
            "imagen-4.0-generate-001",        # Imagen 4 GA
            "imagen-4.0-fast-generate-001"    # Imagen 4 Fast
        ],
        help="Gemini models are more broadly available. Imagen models often require Vertex AI or an allowlisted API key."
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
        
        with st.spinner(f"Generating {num_images} images using {model_choice}..."):
            try:
                cols = st.columns(2)
                
                # --- BRANCH 1: IMAGEN MODELS ---
                if "imagen" in model_choice:
                    response = client.models.generate_images(
                        model=model_choice,
                        prompt=prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=num_images,
                            aspect_ratio=aspect_ratio,
                            output_mime_type="image/jpeg"
                        )
                    )
                    for i, generated_image in enumerate(response.generated_images):
                        img = PIL.Image.open(io.BytesIO(generated_image.image.image_bytes))
                        cols[i % 2].image(img, use_container_width=True, caption=f"Variant {i+1}")

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
                    
                    image_count = 0
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if part.inline_data:
                                img = PIL.Image.open(io.BytesIO(part.inline_data.data))
                                cols[image_count % 2].image(img, use_container_width=True, caption=f"Variant {image_count+1}")
                                image_count += 1
                                
            except Exception as e:
                st.error(f"Error: {e}")
                if "404" in str(e):
                    st.info("💡 **404 Tip:** Your API key does not have access to this specific model. Try one of the `gemini` image models from the dropdown instead!")

st.divider()
st.caption("Powered by Google GenAI.")
