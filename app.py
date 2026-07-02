import streamlit as st
from pypdf import PdfReader
import io
from transformers import pipeline
import easyocr
import numpy as np
from pdf2image import convert_from_bytes

# 1. App Title and Description
st.title("🧪 Chemical IUPAC Name Extractor (With OCR)")
st.write("Upload any PDF (digital or scanned image). The app will use OCR if needed to extract chemical names.")

uploaded_file = st.file_uploader("Upload your PDF here", type=["pdf"], key="robust_uploader")

# Load the specialized Chemical AI Model
@st.cache_resource
def load_model():
    return pipeline("ner", model="samuel95/bert-base-chemical", aggregation_strategy="simple")

# Load OCR Reader
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en']) # 'en' stands for English

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
            
            # 3. Trigger OCR if no text was found (Scanned PDF)
            if not raw_text.strip():
                st.info("No digital text layer found. Activating OCR to read scanned image pages... (This may take a minute)")
                
                # Convert PDF pages to images
                images = convert_from_bytes(file_bytes)
                ocr_reader = load_ocr()
                
                for i, image in enumerate(images):
                    with st.spinner(f"OCR reading page {i+1} of {len(images)}..."):
                        # Convert PIL image to numpy array for EasyOCR
                        img_np = np.array(image)
                        result = ocr_reader.readtext(img_np, detail=0)
                        raw_text += " ".join(result) + "\n"
            
            # 4. Analyze text with AI if we found something
            if not raw_text.strip():
                st.error("OCR could not read any text from this document. Please ensure the image is clear.")
            else:
                st.info(f"Successfully extracted text. Processing with AI...")
                
                with st.spinner("Analyzing text for chemical names..."):
                    nlp = load_model()
                    # Feed text to the model (limiting characters slightly for speed)
                    ner_results = nlp(raw_text[:20000]) 
                    
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
