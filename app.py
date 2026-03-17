import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io

# --- Page Config ---
st.set_page_config(page_title="Gemini & Nano Banana Studio", layout="wide", page_icon="🎨")

# --- WARNING: HARDCODED API KEY ---
# It is strongly recommended to use st.secrets["API_KEY"] in production!
API_KEY = "AIzaSyDzOzblDxp1i_sqdyufGTz1xCPK4ZzhxNg"

# --- Sidebar Configuration ---
with st.sidebar:
    st.title("⚙️ Settings")
    
    # Model Selection
    model_choice = st.selectbox(
        "Choose a Model",
        options=["Nano Banana Pro", "Nano Banana 2", "Gemini 3 Flash"]
    )
    
    # Only show image settings if an image model is selected
    if "Banana" in model_choice:
        aspect_ratio = st.selectbox("Aspect Ratio", options=["1:1", "4:3", "3:4", "16:9", "9:16"], index=0)
        num_images = st.slider("Number of Images", min_value=1, max_value=4, value=1)
        # Note: 'resolution' is kept in the UI for your design, but is not passed directly 
        # to the standard API config to prevent the Pydantic 'extra inputs' error.
        resolution = st.selectbox("Resolution", options=["1K", "2K", "4K"], index=0)
    else:
        st.info("💡 Gemini 3 Flash is a text model. Image settings are hidden.")

# --- Main UI ---
st.header(f"✨ Generating with {model_choice}")

prompt = st.text_area(
    "What do you want to create or ask?",
    placeholder="e.g., A cinematic shot of a futuristic city OR Write a story about a futuristic city...",
    height=150
)

if st.button("Generate"):
    if not prompt:
        st.warning("Please enter a prompt first!")
    else:
        try:
            # Initialize the new Google GenAI Client
            client = genai.Client(api_key=API_KEY)
            
            with st.spinner(f"Processing with {model_choice}..."):
                
                # --- IMAGE GENERATION BRANCH ---
                if "Banana" in model_choice:
                    # Map your UI names to the official API model strings
                    api_model_name = "gemini-3-flash-image" if model_choice == "Nano Banana 2" else "gemini-3-pro-image"
                    
                    response = client.models.generate_image(
                        model=api_model_name,
                        prompt=prompt,
                        config=types.GenerateImageConfig(
                            aspect_ratio=aspect_ratio,
                            number_of_images=num_images,
                            output_mime_type="image/jpeg"
                        )
                    )
                    
                    # Display the images
                    if response.generated_images:
                        cols = st.columns(min(num_images, 2)) # Dynamic grid
                        for idx, generated_image in enumerate(response.generated_images):
                            image_bytes = generated_image.image.image_bytes
                            img = PIL.Image.open(io.BytesIO(image_bytes))
                            with cols[idx % 2]:
                                st.image(img, use_container_width=True, caption=f"Generated at {resolution}")
                    else:
                        st.error("No images generated. This might be due to safety filters.")

                # --- TEXT GENERATION BRANCH ---
                elif model_choice == "Gemini 3 Flash":
                    response = client.models.generate_content(
                        model="gemini-3-flash",
                        contents=prompt
                    )
                    
                    # Display the text
                    if response.text:
                        st.markdown("### Response:")
                        st.write(response.text)
                    else:
                        st.error("No text generated.")
                        
        except Exception as e:
            # Catch Pydantic or API errors and display them cleanly
            st.error(f"Error: {str(e)}")

st.markdown("---")
st.caption("Using Gemini Ultra Cloud Credits via API. Keep your API keys safe!")
