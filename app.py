import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io
import cloudinary
import cloudinary.uploader
import cloudinary.api
import uuid

st.set_page_config(page_title="My Private Flow", layout="wide")
st.title("🎨 Multi-Gen Image Studio (Nano Banana)")

# --- Configure Cloudinary ---
# We try to load secrets safely so the app doesn't crash if they are missing
try:
    cloudinary.config(
        cloud_name=st.secrets.get("CLOUDINARY_CLOUD_NAME", ""),
        api_key=st.secrets.get("CLOUDINARY_API_KEY", ""),
        api_secret=st.secrets.get("CLOUDINARY_API_SECRET", ""),
        secure=True
    )
except Exception:
    pass # Will handle missing credentials gracefully in the UI

# --- Session State ---
if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

# --- Helper Function ---
def get_closest_aspect_ratio(image: PIL.Image.Image) -> str:
    w, h = image.size
    ratio = w / h
    ratios = {"1:1": 1.0, "16:9": 1.777, "9:16": 0.562, "4:3": 1.333, "3:4": 0.75}
    return min(ratios.keys(), key=lambda k: abs(ratios[k] - ratio))

def delete_image(index, public_id):
    """Deletes image from Cloudinary and removes it from session state."""
    try:
        cloudinary.uploader.destroy(public_id)
        st.session_state.generated_images.pop(index)
        st.toast(f"Image deleted from Cloudinary!")
    except Exception as e:
        st.error(f"Failed to delete: {e}")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Project Folder Name
    project_name = st.text_input("Project Folder Name", value="My_Flow_Generations", help="Images will be saved in this Cloudinary folder.")
    
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
    cloud_name = st.secrets.get("CLOUDINARY_CLOUD_NAME", "")
    
    if not api_key:
        st.error("Please enter your API Key in the sidebar or add it to Streamlit secrets.")
    elif not cloud_name:
        st.error("Please configure your Cloudinary credentials in Streamlit secrets.")
    elif not prompt:
        st.warning("Please enter a prompt.")
    else:
        client = genai.Client(api_key=api_key)
        
        # We don't clear the session state here anymore so you can build a gallery!
        # If you want it to clear on every generation, uncomment the line below:
        # st.session_state.generated_images = [] 
        
        if aspect_ratio_choice == "Auto":
            if input_image:
                api_aspect_ratio = get_closest_aspect_ratio(input_image)
                st.toast(f"Auto Aspect Ratio snapped to {api_aspect_ratio}")
            else:
                api_aspect_ratio = "1:1"
                st.toast("No image uploaded. Auto defaulted to 1:1.")
        else:
            api_aspect_ratio = aspect_ratio_choice
        
        with st.spinner(f"Generating {num_images} images and uploading to Cloudinary..."):
            try:
                contents_list = [prompt]
                if input_image:
                    contents_list.append(input_image)
                    
                for _ in range(num_images):
                    response = client.models.generate_content(
                        model=model_choice,
                        contents=contents_list,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"],
                            image_config=types.ImageConfig(
                                aspect_ratio=api_aspect_ratio
                            )
                        )
                    )
                    
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if part.inline_data:
                                img_bytes = part.inline_data.data
                                
                                # --- Upload to Cloudinary ---
                                upload_result = cloudinary.uploader.upload(
                                    io.BytesIO(img_bytes),
                                    folder=project_name,
                                    public_id=f"flow_gen_{uuid.uuid4().hex[:8]}", # Unique ID
                                    resource_type="image"
                                )
                                
                                # Store the dictionary with Cloudinary metadata
                                st.session_state.generated_images.append({
                                    "bytes": img_bytes,
                                    "url": upload_result.get("secure_url"),
                                    "public_id": upload_result.get("public_id")
                                })
                                
            except Exception as e:
                st.error(f"Error: {e}")

# --- Display Results & Action Buttons ---
if st.session_state.generated_images:
    st.subheader(f"📂 Project Gallery: {project_name}")
    
    # We use dynamic columns so it wraps nicely
    cols = st.columns(2)
    
    for i, img_data in enumerate(st.session_state.generated_images):
        with cols[i % 2]:
            # Load image from bytes
            img = PIL.Image.open(io.BytesIO(img_data["bytes"]))
            st.image(img, use_container_width=True, caption=f"Variant {i+1}")
            
            btn_cols = st.columns(3) # Added a 3rd column for Delete
            
            # Download Button
            with btn_cols[0]:
                st.download_button(
                    label="⬇️ Download",
                    data=img_data["bytes"],
                    file_name=f"flow_generation_{i+1}.jpeg",
                    mime="image/jpeg",
                    use_container_width=True,
                    key=f"dl_{i}_{img_data['public_id']}"
                )
            
            # Upscale Button
            with btn_cols[1]:
                if image_quality != "4K":
                    if st.button("✨ Upscale", use_container_width=True, key=f"up_{i}_{img_data['public_id']}"):
                        st.info("Upscale logic here!")
            
            # Delete Button
            with btn_cols[2]:
                # We use on_click to trigger the deletion and rerun the UI
                st.button(
                    "🗑️ Delete", 
                    use_container_width=True, 
                    key=f"del_{i}_{img_data['public_id']}",
                    on_click=delete_image,
                    args=(i, img_data["public_id"])
                )

st.divider()
st.caption("Powered by Google GenAI & Cloudinary.")
