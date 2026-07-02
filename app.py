import streamlit as st
from pypdf import PdfReader
import io
import re

# 1. App Title and Description
st.title("🧪 Chemical IUPAC Name Extractor")
st.write("Upload a digital scientific PDF to instantly scan and extract its IUPAC chemical names.")

uploaded_file = st.file_uploader("Upload your digital PDF here", type=["pdf"], key="clean_uploader")

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
    with st.spinner("Scanning digital PDF text layer..."):
        try:
            raw_text = ""
            file_bytes = uploaded_file.read()
            
            # Extract text from digital layers
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            for page in reader.pages:
                text_content = page.extract_text()
                if text_content:
                    raw_text += text_content + "\n"
            
            # 3. Check if text extraction worked
            if not raw_text.strip():
                st.error("Could not extract any text. This looks like a scanned image PDF. Please upload a searchable, digital PDF document.")
            else:
                st.info("Text successfully extracted. Sorting chemical terms...")
                chemical_names = extract_iupac_patterns(raw_text)

                # 4. Output results
                if chemical_names:
                    st.success(f"Found {len(chemical_names)} unique chemical names!")
                    st.write("### Extracted IUPAC / Chemical Names:")
                    
                    for name in chemical_names:
                        st.write(f"- {name}")
                        
                    csv = "\n".join(chemical_names)
                    st.download_button("Download List as CSV", csv, "chemicals.csv", "text/csv")
                else:
                    st.warning("No standard chemical names matching IUPAC rules were detected in the text layer.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
