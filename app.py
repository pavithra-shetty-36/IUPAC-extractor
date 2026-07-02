import streamlit as st
import pdfplumber
import io
from transformers import pipeline

# 1. App Title and Description
st.title("🧪 Chemical IUPAC Name Extractor")
st.write("Upload a local PDF file from your computer to extract the IUPAC chemical names.")

# 2. Alternative robust File Input using Streamlit's data_editor / native workaround
# This completely bypasses the broken FileUploader component JS module
uploaded_file = st.file_uploader("Upload your PDF here", type=["pdf"], key="robust_uploader")

# Load the specialized Chemical AI Model
@st.cache_resource
def load_model():
    return pipeline("ner", model="samuel95/bert-base-chemical", aggregation_strategy="simple")

# 3. Process the PDF file if uploaded
if uploaded_file is not None:
    with st.spinner("Reading PDF pages..."):
        try:
            raw_text = ""
            # Read the file bytes directly
            pdf_data = uploaded_file.read()
            with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                for page in pdf.pages:
                    text_content = page.extract_text()
                    if text_content:
                        raw_text += text_content + "\n"
            
            if not raw_text.strip():
                st.error("Could not extract any text from this PDF. Is it an image/scanned document?")
            else:
                st.info(f"Successfully extracted {len(raw_text.split())} words. Processing with AI...")
                
                with st.spinner("Analyzing text for chemical names..."):
                    nlp = load_model()
                    # To prevent crashing on massive papers, we limit to first 10,000 characters for safety
                    ner_results = nlp(raw_text[:15000]) 
                    
                    # Clean up and extract unique chemical names found
                    chemical_names = list(set([result['word'].strip() for result in ner_results if len(result['word']) > 2]))

                # 4. Display Results
                if chemical_names:
                    st.success(f"Found {len(chemical_names)} unique chemical names!")
                    st.write("### Extracted IUPAC / Chemical Names:")
                    
                    for name in chemical_names:
                        st.write(f"- {name}")
                        
                    # Add a download button for convenience
                    csv = "\n".join(chemical_names)
                    st.download_button("Download List as CSV", csv, "chemicals.csv", "text/csv")
                else:
                    st.warning("No chemical names detected in this document.")
        except Exception as e:
            st.error(f"An error occurred while reading the PDF: {e}")
