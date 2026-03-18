import streamlit as st
import traceback

st.set_page_config(page_title="My Private Flow", layout="wide")

# --- 1. SAFE IMPORTS ---
try:
    from google import genai
    from google.genai import types
    import PIL.Image
    import io
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    from streamlit_drawable_canvas import st_canvas
    import numpy as np
except ImportError as e:
    st.error(f"🚨 Import Error: {e}")
    st.info("Please make sure your requirements.txt is updated and Streamlit has finished installing them. You may need to click 'Manage App' -> 'Reboot' in the Streamlit menu.")
    st.stop()

st.title("🎨 Gemini 3.1: Multi-Gen & Editor")

# --- 2. SAFE SECRETS LOADING ---
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    cloud_name = st.secrets.get("CLOUDINARY_CLOUD_NAME", "")
    cloud_api_key = st.secrets.get("CLOUDINARY_API_KEY", "")
    cloud_api_secret = st.secrets.get("CLOUDINARY_API_SECRET", "")
    
    if cloud_name and cloud_api_key and cloud_api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=cloud_api_key,
            api_secret=cloud_api_secret
        )
except Exception as e:
    st.error(f"🚨 Error loading secrets: {e}")
    st.info("Check your .streamlit/secrets.toml formatting.")
    st.stop()

if not api_key:
    st.warning("⚠️ Please configure your GEMINI_API_KEY in Streamlit secrets.")
    st.stop()

# --- 3. SAFE GEMINI INIT ---
try:
    client = genai.Client(api_key=api_key)
    MODEL_CHOICE = "gemini-3.1-flash-image-preview"
except Exception as e:
    st.error(f"🚨 Failed to initialize Gemini Client: {e}")
    st.stop()

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
        uploaded_refs = st.file_uploader("Upload Reference Images (Optional)", accept_multiple_files=True, type=["png", "jpg", "jpeg"])
        prompt = st.text_area("What do you want to see?", placeholder="A futuristic city at sunset...")
        generate_btn = st.button("Generate (1K Default)", type="primary", use_container_width=True)

    with col2:
        st.subheader("Output")
        
        if generate_btn and prompt:
            with st.spinner("Generating image at 1K..."):
                try:
                    contents = [prompt]
                    if uploaded_refs:
                        for ref in uploaded_refs:
                            contents.append(PIL.Image.open(ref))
                    
                    response = client.models.generate_content(
                        model=MODEL_CHOICE,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            image_config=types.ImageConfig(
                                aspect_ratio=aspect_ratio,
                                image_size="1K"
                            )
                        )
                    )
                    
                    img = None
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if part.inline_data:
                                img = PIL.Image.open(io.BytesIO(part.inline_data.data))
                                break
                        if img: break
                        
                    if img:
                        st.session_state['current_image'] = img
                        st.session_state['current_prompt'] = prompt
                    else:
                        st.error("No image returned by the model.")
                except Exception as e:
                    st.error(f"Generation Error: {e}")
                    st.code(traceback.format_exc())

        if 'current_image' in st.session_state:
            st.image(st.session_state['current_image'], use_container_width=True, caption="Generated Image")
            
            action_col1, action_col2 = st.columns(2)
            
            with action_col1:
                if st.button("❤️ Like & Save to Gallery", use_container_width=True):
                    with st.spinner("Saving to Cloudinary..."):
                        buf = io.BytesIO()
                        st.session_state['current_image'].save(buf, format='PNG')
                        try:
                            cloudinary.uploader.upload(
                                buf.getvalue(), 
                                folder="my_flow/liked", 
                                tags=["liked"]
                            )
                            st.success("Saved to Liked Gallery!")
                        except Exception as e:
                            st.error(f"Cloudinary Error: {e}")
                            st.code(traceback.format_exc())
            
            with action_col2:
                if st.button("🔍 Upscale to 4K", use_container_width=True):
                    with st.spinner("Upscaling to 4K..."):
                        try:
                            contents = [st.session_state['current_prompt']]
                            if uploaded_refs:
                                for ref in uploaded_refs:
                                    contents.append(PIL.Image.open(ref))
                                    
                            response = client.models.generate_content(
                                model=MODEL_CHOICE,
                                contents=contents,
                                config=types.GenerateContentConfig(
                                    image_config=types.ImageConfig(
                                        aspect_ratio=aspect_ratio,
                                        image_size="4K"
                                    )
                                )
                            )
                            
                            img_4k = None
                            for candidate in response.candidates:
                                for part in candidate.content.parts:
                                    if part.inline_data:
                                        img_4k = PIL.Image.open(io.BytesIO(part.inline_data.data))
                                        break
                                if img_4k: break
                                
                            if img_4k:
                                st.session_state['current_image'] = img_4k
                                st.rerun()
                            else:
                                st.error("No image returned during upscale.")
                        except Exception as e:
                            st.error(f"Upscale Error: {e}")
                            st.code(traceback.format_exc())

# ==========================================
# TAB 2: EDITING (MASKING)
# ==========================================
with tab_edit:
    st.subheader("Draw a mask to edit specific areas")
    edit_file = st.file_uploader("Upload an image to edit", type=["png", "jpg", "jpeg"], key="edit_uploader")
    
    if edit_file:
        try:
            bg_image = PIL.Image.open(edit_file).convert("RGBA")
            
            st.write("Draw over the area you want to change:")
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 1)",
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
                            mask_image = PIL.Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                            
                            response = client.models.generate_content(
                                model=MODEL_CHOICE,
                                contents=[bg_image, mask_image, edit_prompt]
                            )
                            
                            edited_img = None
                            for candidate in response.candidates:
                                for part in candidate.content.parts:
                                    if part.inline_data:
                                        edited_img = PIL.Image.open(io.BytesIO(part.inline_data.data))
                                        break
                                if edited_img: break
                                
                            if edited_img:
                                st.image(edited_img, caption="Edited Result", use_container_width=True)
                            else:
                                st.error("No image returned by the model.")
                        except Exception as e:
                            st.error(f"Editing Error: {e}")
                            st.code(traceback.format_exc())
        except Exception as e:
            st.error(f"Error loading image for editing: {e}")

# ==========================================
# TAB 3: LIKED GALLERY
# ==========================================
with tab_gallery:
    st.subheader("Your Liked Images")
    if st.button("🔄 Refresh Gallery"):
        st.rerun()
        
    try:
        if cloud_name and cloud_api_key and cloud_api_secret:
            resources = cloudinary.api.resources(
                type="upload", 
                prefix="my_flow/liked/", 
                max_results=20
            )
            
            images = resources.get("resources", [])
            
            if not images:
                st.info("No liked images yet. Go generate and like some!")
            else:
                cols = st.columns(3)
                for i, img_data in enumerate(images):
                    with cols[i % 3]:
                        st.image(img_data["secure_url"], use_container_width=True)
        else:
            st.warning("Cloudinary secrets are missing. Cannot load gallery.")
    except Exception as e:
        st.error("Could not load gallery.")
        st.code(traceback.format_exc())
