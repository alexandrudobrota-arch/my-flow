import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io
import cloudinary
import cloudinary.uploader
import cloudinary.api
import uuid

# --- Page Config & Custom CSS ---
st.set_page_config(page_title="Bullseye Media House", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    header { background-color: transparent !important; }
    h1, h2, h3 { color: #ff6b00 !important; font-family: 'Arial Black', sans-serif; text-transform: uppercase; letter-spacing: 1.5px; }
    .stButton>button { background-color: #ff6b00; color: #ffffff; font-weight: 800; border: none; border-radius: 4px; text-transform: uppercase; transition: all 0.3s ease-in-out; }
    .stButton>button:hover { background-color: #ff8533; transform: scale(1.02); box-shadow: 0 0 15px rgba(255, 107, 0, 0.4); }
    [data-testid="stSidebar"] { background-color: #121826; border-right: 1px solid #2d3748; }
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea { background-color: #1a202c; color: #ffffff; border: 1px solid #4a5568; border-radius: 4px; }
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
            prefix=f"{folder_name}/", 
            max_results=50
        )
        return result.get("resources", [])
    except Exception:
        return []

# --- Helper Functions ---
def get_closest_aspect_ratio(image: PIL.Image.Image) -> str:
    w, h = image.size
    ratio = w / h
    ratios = {"1:1": 1.0, "16:9": 1.777, "9:16": 0.562, "4:3": 1.333, "3:4": 0.75}
    return min(ratios.keys(), key=lambda k: abs(ratios[k] - ratio))

def delete_generated_image(index, public_id):
    try:
        cloudinary.uploader.destroy(public_id)
        st.session_state.generated_images.pop(index)
        st.toast("Image deleted from Cloudinary!")
    except Exception as e:
        st.error(f"Failed to delete: {e}")

def delete_vault_image(public_id):
    try:
        cloudinary.uploader.destroy(public_id)
        get_images_in_folder.clear() 
        st.toast("Vault image deleted from Cloudinary!")
    except Exception as e:
        st.error(f"Failed to delete: {e}")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Project Config")
    project_name = st.text_input("Active Project Folder", value="Bullseye_Assets", help="Generations will be saved here.")
    api_key_input = st.text_input("Enter Gemini API Key (or use Secrets)", type="password")
    
    st.divider()
    st.header("🧠 Model Settings")
    model_choice = st.selectbox(
        "Select Engine",
        [
            "gemini-3.1-flash-image-preview", 
            "gemini-3-pro-image-preview",     
            "gemini-2.5-flash-image"          
        ]
    )
    
    uploaded_file = st.file_uploader("Upload Reference Plate", type=["png", "jpg", "jpeg"])
    input_image = None
    if uploaded_file:
        input_image = PIL.Image.open(uploaded_file)
        st.image(input_image, caption="Reference Plate", use_container_width=True)
    
    image_quality = st.selectbox("Output Quality", ["1K", "2K", "4K"])
    aspect_ratio_choice = st.selectbox("Aspect Ratio", ["Auto", "1:1", "16:9", "9:16", "4:3", "3:4"])
    num_images = st.slider("Batch Size", 1, 4, 4)

# --- Main Gen UI ---
prompt = st.text_area("Asset Description Prompt", placeholder="A highly detailed cyberpunk metaverse city, neon lights, unreal engine 5 style...")

if st.button("Generate Assets"):
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    cloud_name = st.secrets.get("CLOUDINARY_CLOUD_NAME", "")
    
    if not api_key:
        st.error("Missing Gemini API Key.")
    elif not cloud_name:
        st.error("Missing Cloudinary credentials.")
    elif not prompt:
        st.warning("Please enter a prompt.")
    else:
        client = genai.Client(api_key=api_key)
        
        if aspect_ratio_choice == "Auto":
            if input_image:
                api_aspect_ratio = get_closest_aspect_ratio(input_image)
                st.toast(f"Auto Aspect Ratio snapped to {api_aspect_ratio}")
            else:
                api_aspect_ratio = "1:1"
        else:
            api_aspect_ratio = aspect_ratio_choice
        
        with st.spinner("Rendering assets & syncing to Cloudinary..."):
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
                            image_config=types.ImageConfig(aspect_ratio=api_aspect_ratio)
                        )
                    )
                    
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if part.inline_data:
                                img_bytes = part.inline_data.data
                                upload_result = cloudinary.uploader.upload(
                                    io.BytesIO(img_bytes),
                                    folder=project_name,
                                    public_id=f"asset_{uuid.uuid4().hex[:8]}",
                                    resource_type="image"
                                )
                                st.session_state.generated_images.append({
                                    "bytes": img_bytes,
                                    "url": upload_result.get("secure_url"),
                                    "public_id": upload_result.get("public_id")
                                })
                get_cloudinary_folders.clear()
                get_images_in_folder.clear()
                                
            except Exception as e:
                st.error(f"Generation Error: {e}")

# --- Current Session Gallery ---
if st.session_state.generated_images:
    st.subheader("🔥 Current Session Output")
    cols = st.columns(2)
    for i, img_data in enumerate(st.session_state.generated_images):
        with cols[i % 2]:
            img = PIL.Image.open(io.BytesIO(img_data["bytes"]))
            st.image(img, use_container_width=True, caption=f"Render {i+1}")
            
            btn_cols = st.columns(3)
            with btn_cols[0]:
                st.download_button("⬇️ DL", img_data["bytes"], f"render_{i+1}.jpeg", "image/jpeg", use_container_width=True, key=f"dl_gen_{i}")
            with btn_cols[1]:
                if image_quality != "4K":
                    st.button("✨ 4K", use_container_width=True, key=f"up_gen_{i}")
            with btn_cols[2]:
                st.button("🗑️ Del", use_container_width=True, key=f"del_gen_{i}", on_click=delete_generated_image, args=(i, img_data["public_id"]))

st.divider()

# --- MEDIA VAULT (Cloudinary Integration) ---
st.header("🗄️ Media Vault")
available_folders = get_cloudinary_folders()

if not available_folders:
    st.info("No folders found in Cloudinary yet. Generate some images first!")
else:
    selected_vault_folder = st.selectbox("Browse Project Folders", available_folders)
    vault_images = get_images_in_folder(selected_vault_folder)
    
    if not vault_images:
        st.info("Folder is empty.")
    else:
        st.caption(f"Found {len(vault_images)} assets in '{selected_vault_folder}'")
        vault_cols = st.columns(4) 
        
        for idx, v_img in enumerate(vault_images):
            with vault_cols[idx % 4]:
                st.image(v_img["secure_url"], use_container_width=True)
                
                v_btn_cols = st.columns(2)
                with v_btn_cols[0]:
                    st.link_button("⬇️", v_img["secure_url"], use_container_width=True)
                with v_btn_cols[1]:
                    st.button("🗑️", use_container_width=True, key=f"del_vault_{v_img['public_id']}", on_click=delete_vault_image, args=(v_img["public_id"],))

st.caption("Powered by Google GenAI & Cloudinary | Bullseye Media House ©")
# --- END OF APP.PY ---
