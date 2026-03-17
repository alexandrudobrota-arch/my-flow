import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io

st.set_page_config(page_title="My Private Flow", layout="wide")
st.title("🎨 Multi-Gen Image Studio (Nano Banana)")

# --- Session State ---
if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

# --- Helper Function ---
def get_closest_aspect_ratio(image: PIL.Image.Image) -> str:
    w, h = image.size
    ratio = w / h
    ratios = {"1:1": 1.0, "16:9": 1.777, "9:16": 0.562, "4:3": 1.333, "3:4": 0.75}
    return min(ratios.keys(), key=lambda k: abs(ratios[k] - ratio))

# --- Sidebar Configuration ---
with st.sidebar:
    api_key_input = st.text_input("Enter Gemini API Key (or leave blank for Secrets)", type="password")
    
    model_choice = st.selectbox(
        "Select Model",
        [
            "gemini-3.1-flash-image-preview", # Nano Banana 2
            "gemini-3-pro-image-preview",     # Nano Banana Pro
            "gemini-2.5-flash-image"          # Nano Banana (Stable)
        ]
    )
    
    uploaded_file = st.file_uploader("Upload Reference Image", type=["png", "jpg", "jpeg"])
    input_image = None
    if uploaded_file:
        input_image = PIL.Image.open(uploaded_file)
        st.image(input_image, caption="Reference Image", use_container_width=True)
    
    image_quality = st.selectbox("Image Quality", ["1K", "2K", "4K"])
    aspect_ratio_choice = st.selectbox("Aspect Ratio", ["Auto", "1:1", "16:9", "9:16", "4:3", "3:4"])
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
        st.session_state.generated_images = [] 
        
        if aspect_ratio_choice == "Auto":
            if input_image:
                api_aspect_ratio = get_closest_aspect_ratio(input_image)
                st.toast(f"Auto Aspect Ratio snapped to {api_aspect_ratio}")
            else:
                api_aspect_ratio = "1:1"
                st.toast("No image uploaded. Auto defaulted to 1:1.")
        else:
            api_aspect_ratio = aspect_ratio_choice
        
        with st.spinner(f"Generating {num_images} images using {model_choice}..."):
            try:
                contents_list = [prompt]
                if input_image:
                    contents_list.append(input_image)
                    
                # --- THE FIX: We loop the request instead of using candidate_count ---
                for _ in range(num_images):
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=contents_list,
                        config=types.GenerateContentConfig(
                            # Removed candidate_count entirely
                            response_modalities=["IMAGE"],
                            image_config=types.ImageConfig(
                                aspect_ratio=api_aspect_ratio
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
            img = PIL.Image.open(io.BytesIO(img_bytes))
            st.image(img, use_container_width=True, caption=f"Variant {i+1}")
            
            btn_cols = st.columns(2)
            with btn_cols[0]:
                st.download_button(
                    label="⬇️ Download",
                    data=img_bytes,
                    file_name=f"flow_generation_{i+1}.jpeg",
                    mime="image/jpeg",
                    use_container_width=True,
                    key=f"dl_{i}"
                )
            
            with btn_cols[1]:
                if image_quality != "4K":
                    if st.button("✨ Upscale to 4K", use_container_width=True, key=f"up_{i}"):
                        st.info("Upscale logic would execute here!")

st.divider()
st.caption("Powered by Google GenAI.")
