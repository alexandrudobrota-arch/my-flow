import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io

# --- Page Config ---
st.set_page_config(page_title="Nano Banana Pro: Multi-Gen", layout="wide")

# --- Sidebar Configuration ---
with st.sidebar:
    st.title("Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    
    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        options=["1:1", "4:3", "3:4", "16:9", "9:16"],
        index=0
    )
    
    num_images = st.slider("Number of Images", min_value=1, max_value=4, value=4)
    
    # Resolution logic (simplified for the SDK)
    resolution = st.select_slider("Resolution", options=["256", "512", "1K"], value="1K")

# --- Main UI ---
st.header("🎨 Nano Banana Pro: Multi-Gen")

prompt = st.text_area(
    "What do you want to see?",
    placeholder="e.g., A futuristic city at sunset, cinematic lighting...",
    height=150
)

if st.button("Generate Images"):
    if not api_key:
        st.error("Please enter your API Key in the sidebar.")
    elif not prompt:
        st.warning("Please enter a prompt.")
    else:
        try:
            # 1. Initialize the Client
            client = genai.Client(api_key=api_key)

            with st.spinner("Generating magic..."):
                # 2. Use generate_image (NOT generate_content)
                # 3. Use GenerateImageConfig (NOT GenerateContentConfig)
                response = client.models.generate_image(
                    model='gemini-3-flash-image',  # Official name for Nano Banana 2/Pro
                    prompt=prompt,
                    config=types.GenerateImageConfig(
                        aspect_ratio=aspect_ratio,
                        number_of_images=num_images,
                        output_mime_type='image/jpeg'
                    )
                )

                # 4. Display the results
                if response.generated_images:
                    cols = st.columns(2)  # Create a grid
                    for idx, generated_image in enumerate(response.generated_images):
                        # Convert bytes to an image object
                        image_bytes = generated_image.image.image_bytes
                        img = PIL.Image.open(io.BytesIO(image_bytes))
                        
                        # Place in the grid
                        with cols[idx % 2]:
                            st.image(img, use_container_width=True, caption=f"Generation {idx+1}")
                else:
                    st.error("No images were generated. Check your prompt safety filters.")

        except Exception as e:
            # This captures the Pydantic or API errors and shows them clearly
            st.error(f"Error: {str(e)}")

st.markdown("---")
st.caption("Using Gemini Ultra Cloud Credits via API.")
