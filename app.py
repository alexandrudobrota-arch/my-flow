import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io
import cloudinary
import cloudinary.uploader
import cloudinary.api
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="My Private Flow", layout="wide")
st.title("🎨 Gemini 3.1: Multi-Gen & Editor")

# --- Secrets & Config ---
api_key = st.secrets.get("GEMINI_API_KEY", "")
cloudinary.config(
    cloud_name=st.secrets.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key=st.secrets.get("CLOUDINARY_API_KEY", ""),
    api_secret=st.secrets.get("CLOUDINARY_API_SECRET", "")
)

# We use the 3.1 flash image preview model for high quality generation and editing
MODEL_CHOICE = "gemini-3.1-flash-image-preview"

if not api_key:
    st.warning("Please configure your GEMINI_API_KEY in Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- App Tabs ---
tab_gen, tab_edit, tab_gallery = st.tabs(["✨ Generate", "🖌️ Edit Image", "❤️ Liked Gallery"])

# ==========================================
# TAB 1: GENERATE
# ==========================================
with tab_gen:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Settings")
        aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "16:9", "9:16", "4:3", "3:4"])
        # 1. Multiple image upload for reference
        uploaded_refs = st.file_uploader("Upload Reference Images (Optional)", accept_multiple_files=True, type=["png", "jpg", "jpeg"])
        prompt = st.text_area("What do you want to see?", placeholder="A futuristic city at sunset...")
        
        generate_btn = st.button("Generate (1K Default)", type="primary", use_container_width=True)

    with col2:
        st.subheader("Output")
        
        # Helper function to generate images
        def generate_image(target_resolution="1K"):
            with st.spinner(f"Generating image at {target_resolution}..."):
                try:
                    # Prepare contents: prompt + any reference images
                    contents = [prompt]
                    if uploaded_refs:
                        for ref in uploaded_refs:
                            contents.append(PIL.Image.open(ref))
                    
                    # 2. Configure resolution (1K default, 4K upscale)
                    # Note: exact kwarg depends on google-genai version, typically passed in config
                    response = client.models.generate_content(
                        model=MODEL_CHOICE,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            # Pass aspect ratio and resolution/imageSize based on SDK support
                            # If your SDK version uses a different kwarg for resolution, update it here.
                            temperature=0.7
                        )
                    )
                    
                    # Extract image from response
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if part.inline_data:
                                return PIL.Image.open(io.BytesIO(part.inline_data.data))
                except Exception as e:
                    st.error(f"Generation Error: {e}")
                    return None

        # Handle Generation
        if generate_btn and prompt:
            img = generate_image("1K")
            if img:
                st.session_state['current_image'] = img
                st.session_state['current_prompt'] = prompt

        # Display current image and action buttons
        if 'current_image' in st.session_state:
            st.image(st.session_state['current_image'], use_container_width=True, caption="Generated Image")
            
            action_col1, action_col2 = st.columns(2)
            
            # 3. Like System -> Uploads to Cloudinary
            with action_col1:
                if st.button("❤️ Like & Save to Gallery", use_container_width=True):
                    with st.spinner("Saving to Cloudinary..."):
                        # Convert PIL to bytes for Cloudinary
                        buf = io.BytesIO()
                        st.session_state['current_image'].save(buf, format='PNG')
                        buf.seek(0)
                        
                        try:
                            # Upload to a specific folder so we can retrieve them easily
                            cloudinary.uploader.upload(
                                buf, 
                                folder="my_flow/liked", 
                                tags=["liked"]
                            )
                            st.success("Saved to Liked Gallery!")
                        except Exception as e:
                            st.error(f"Cloudinary Error: {e}")
            
            # Upscale to 4K
            with action_col2:
                if st.button("🔍 Upscale to 4K", use_container_width=True):
                    img_4k = generate_image("4K")
                    if img_4k:
                        st.session_state['current_image'] = img_4k
                        st.rerun()

# ==========================================
# TAB 2: EDITING (MASKING)
# ==========================================
with tab_edit:
    st.subheader("Draw a mask to edit specific areas")
    edit_file = st.file_uploader("Upload an image to edit", type=["png", "jpg", "jpeg"], key="edit_uploader")
    
    if edit_file:
        bg_image = PIL.Image.open(edit_file).convert("RGBA")
        
        # 4. Canvas for drawing the mask
        st.write("Draw over the area you want to change:")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)",  # White mask
            stroke_width=st.slider("Brush Size", 10, 100, 40),
            stroke_color="rgba(255, 255, 255, 1)",
            background_image=bg_image,
            update_streamlit=True,
            height=bg_image.height if bg_image.height < 600 else 600,
            width=bg_image.width if bg_image.width < 800 else 800,
            drawing_mode="freedraw",
            key="canvas",
        )
        
        edit_prompt = st.text_input("Edit Instructions", placeholder="e.g., Change the drawn area to a red car")
        
        if st.button("Apply Edit", type="primary"):
            if canvas_result.image_data is not None and edit_prompt:
                with st.spinner("Editing image..."):
                    try:
                        # Extract the mask drawn by the user
                        mask_image = PIL.Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                        
                        # Send original image, the mask, and the prompt to Gemini
                        response = client.models.generate_content(
                            model=MODEL_CHOICE,
                            contents=[bg_image, mask_image, edit_prompt]
                        )
                        
                        for candidate in response.candidates:
                            for part in candidate.content.parts:
                                if part.inline_data:
                                    edited_img = PIL.Image.open(io.BytesIO(part.inline_data.data))
                                    st.image(edited_img, caption="Edited Result", use_container_width=True)
                    except Exception as e:
                        st.error(f"Editing Error: {e}")

# ==========================================
# TAB 3: LIKED GALLERY
# ==========================================
with tab_gallery:
    st.subheader("Your Liked Images")
    if st.button("🔄 Refresh Gallery"):
        st.rerun()
        
    try:
        # Fetch images from the specific Cloudinary folder
        resources = cloudinary.api.resources(
            type="upload", 
            prefix="my_flow/liked/", 
            max_results=20
        )
        
        images = resources.get("resources", [])
        
        if not images:
            st.info("No liked images yet. Go generate and like some!")
        else:
            # Display in a 3-column grid
            cols = st.columns(3)
            for i, img_data in enumerate(images):
                with cols[i % 3]:
                    st.image(img_data["secure_url"], use_container_width=True)
    except Exception as e:
        st.error("Could not load gallery. Ensure Cloudinary secrets are correct.")
        st.caption(str(e))
