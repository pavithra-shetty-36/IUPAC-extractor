import streamlit as st
from pypdf import PdfReader
import io
from transformers import pipeline
import pytesseract
from pdf2image import convert_from_bytes

# 1. App Title and Description
st.title("🧪 Chemical IUPAC Name Extractor")
st.write("Upload any PDF (digital or scanned image). The app will use lightweight OCR if needed.")

uploaded_file = st.file_uploader("Upload your PDF here", type=["pdf"], key="robust_uploader")

# Load the specialized Chemical AI Model
@st.cache_resource
def load_model():
    return pipeline("ner", model="samuel95/bert-base-chemical", aggregation_strategy="simple")

# 2. Process the PDF file if uploaded
if uploaded_file is not None:
    with st.spinner("Reading PDF pages..."):
        try:
            raw_text = ""
            file_bytes = uploaded_file.read()
            
            # Try normal digital extraction first
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            for page in reader.pages:
                text_content = page.extract_text()
                if text_content:
                    raw_text += text_content + "\n"
            
            # 3. Trigger lightweight OCR if no text was found (Scanned PDF)
            if not raw_text.strip():
                st.info("No digital text layer found. Activating lightweight OCR... (This may take a moment)")
                
                # Convert PDF pages to images
                images = convert_from_bytes(file_bytes)
                
                for i, image in enumerate(images):
                    with st.spinner(f"OCR reading page {i+1} of {len(images)}..."):
                        # Use pytesseract instead of heavy deep learning models
                        page_text = pytesseract.image_to_string(image)
                        raw_text += page_text + "\n"
            
            # 4. Analyze text with AI if we found something
            if not raw_text.strip():
                st.error("OCR could not read any text from this document. Please ensure the image is clear.")
            else:
                st.info(f"Successfully extracted text. Processing with AI...")
                
                with st.spinner("Analyzing text for chemical names..."):
                    nlp = load_model()
                    # Feed text to the model (limiting characters slightly for safety)
                    ner_results = nlp(raw_text[:15000]) 
                    
                    # Clean up and extract unique chemical names found
                    chemical_names = list(set([result['word'].strip() for result in ner_results if len(result['word']) > 2]))

                # 5. Display Results
                if chemical_names:
                    st.success(f"Found {len(chemical_names)} unique chemical names!")
                    st.write("### Extracted IUPAC / Chemical Names:")
                    
                    for name in chemical_names:
                        st.write(f"- {name}")
                        
                    # Add a download button
                    csv = "\n".join(chemical_names)
                    st.download_button("Download List as CSV", csv, "chemicals.csv", "text/csv")
                else:
                    st.warning("No chemical names detected in this document.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
