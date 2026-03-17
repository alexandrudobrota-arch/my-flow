import streamlit as st
import google.generativeai as genai
import PIL.Image
import io

# --- Page Config ---
st.set_page_config(page_title="Nano Banana Pro: Multi-Gen", layout="wide", page_icon="🎨")

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
    
    # In the standard SDK, resolution is handled by specific strings or integers
    resolution = st.select_slider("Resolution", options=["256", "512", "1024"], value="1024")

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
            # 1. Configure the API
            genai.configure(api_key=api_key)

            with st.spinner("Generating magic..."):
                # 2. Use ImageGenerationModel (This fixes the 'Models' attribute error)
                # 'imagen-3' or 'gemini-3-flash-image' are the common model strings
                model = genai.ImageGenerationModel("imagen-3")

                # 3. Use generate_images (Note the 's' at the end)
                # This fixes the Pydantic 'aspect_ratio' error
                response = model.generate_images(
                    prompt=prompt,
                    number_of_images=num_images,
                    aspect_ratio=aspect_ratio,
                )

                # 4. Display the results
                if response.images:
                    cols = st.columns(2)  # Create a 2-column grid
                    for idx, img_obj in enumerate(response.images):
                        # The standard SDK returns PIL-ready image objects directly
                        with cols[idx % 2]:
                            st.image(img_obj.image, use_container_width=True, caption=f"Generation {idx+1}")
                else:
                    st.error("No images were returned. This might be due to safety filters.")

        except Exception as e:
            # Displays the error clearly if something goes wrong
            st.error(f"Something went wrong: {str(e)}")

st.markdown("---")
st.caption("Using Gemini Ultra Cloud Credits via API.")
