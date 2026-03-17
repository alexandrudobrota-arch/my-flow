import streamlit as st
import google.generativeai as genai # Needs 'google-generativeai' in requirements.txt
from PIL import Image

# ... (sidebar code same as before) ...

if st.button("Generate Images"):
    try:
        genai.configure(api_key=api_key)
        
        # This class is the most reliable for image generation in this SDK
        model = genai.ImageGenerationModel("imagen-3") 

        response = model.generate_images(
            prompt=prompt,
            number_of_images=num_images,
            aspect_ratio=aspect_ratio
        )

        if response.images:
            for img in response.images:
                st.image(img.image)
                
    except Exception as e:
        st.error(f"Error: {e}")
