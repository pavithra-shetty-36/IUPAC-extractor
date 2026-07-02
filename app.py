import streamlit as st
from pypdf import PdfReader
import io
import re
import pytesseract
from pdf2image import convert_from_bytes

# 1. App Title and Description
st.title("🧪 Chemical IUPAC Name Extractor")
st.write("Upload any PDF (digital or scanned image). This version uses native Tesseract OCR to read scanned text layers safely.")

uploaded_file = st.file_uploader("Upload your PDF here", type=["pdf"], key="robust_uploader")

# Comprehensive pattern match for systematic chemical nomenclature
def extract_iupac_patterns(text):
    chemical_regex = r'\b(?:[0-9,\'\"\-a-Z\s\(\)\[\]]*)?(?:meth|eth|prop|but|pent|hex|hept|oct|non|dec|iso|cyclo|benz|phen|chloro|bromo|fluoro|iodo|amino|nitro|hydroxy|oxo|methyl|ethyl|propyl|butyl|phenyl|benzyl)+(?:ane|ene|yne|ol|one|al|oic\sacid|ate|ic\sacid|ide|ine|ole|azole|in|an|est|yl|oxy|µ|alpha|beta|gamma)s?\b'
    matches = re.findall(chemical_regex, text, re.IGNORECASE)
    
    cleaned_names = []
    for match in matches:
        cleaned = match.strip(" .,()[]-")
        if len(cleaned) > 4 and not cleaned.isdigit() and any(char.isalpha() for char in cleaned):
            cleaned_names.append(cleaned)
            
    return list(set(cleaned_names))

# 2. Process the PDF file if uploaded
if uploaded_file is not None:
    with st.spinner("Processing document..."):
        try:
            raw_text = ""
            file_bytes = uploaded_file.read()
            
            # Try normal digital layer text extraction first
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            for page in reader.pages:
                text_content = page.extract_text()
                if text_content:
                    raw_text += text_content + "\n"
            
            # 3. Trigger Tesseract OCR if no digital text layer is present
            if not raw_text.strip():
                st.info("No digital text layer found. Initializing Tesseract OCR engine...")
                
                # Convert PDF pages to high-quality images (DPI 200) for sharp OCR text matching
                images = convert_from_bytes(file_bytes, dpi=200)
                
                for i, image in enumerate(images):
                    with st.spinner(f"Scanning page {i+1} of {len(images)}..."):
                        # Direct Tesseract image processing
                        page_text = pytesseract.image_to_string(image)
                        raw_text += page_text + "\n"
            
            # 4. Filter text for IUPAC structures
            if not raw_text.strip():
                st.error("The OCR engine could not identify any textual characters. Please ensure the scan is readable.")
            else:
                st.info("Text reading complete. Running chemical text extraction...")
                chemical_names = extract_iupac_patterns(raw_text)

                # 5. Output results
                if chemical_names:
                    st.success(f"Found {len(chemical_names)} unique chemical names!")
                    st.write("### Extracted IUPAC / Chemical Names:")
                    
                    for name in chemical_names:
                        st.write(f"- {name}")
                        
                    csv = "\n".join(chemical_names)
                    st.download_button("Download List as CSV", csv, "chemicals.csv", "text/csv")
                else:
                    st.warning("No standard chemical names matching IUPAC rules were detected.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
