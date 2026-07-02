import streamlit as st
import pdfplumber
from transformers import pipeline

# 1. App Title and Description
st.title("🧪 Chemical IUPAC Name Extractor")
st.write("Upload a scientific PDF, and this app will automatically extract the IUPAC chemical names.")

# 2. File Uploader Component
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

# Load the specialized Chemical AI Model
@st.cache_resource
def load_model():
    # This loads a pre-trained pipeline for Named Entity Recognition (NER) for chemicals
    return pipeline("ner", model="samuel95/bert-base-chemical", aggregation_strategy="simple")

if uploaded_file is not None:
    with st.spinner("Extracting text from PDF..."):
        # 3. Extract text from the uploaded PDF
        raw_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                raw_text += page.extract_text() or ""
        
    with st.spinner("Analyzing text for chemical names..."):
        # 4. Run the AI model over the text
        nlp = load_model()
        ner_results = nlp(raw_text)
        
        # Extract unique chemical names found
        chemical_names = list(set([result['word'] for result in ner_results]))

    # 5. Display Results
    if chemical_names:
        st.success(f"Found {len(chemical_names)} chemical names!")
        st.write("### Extracted IUPAC / Chemical Names:")
        
        # Display as a clean list or table
        for name in chemical_names:
            st.write(f"- {name}")
            
        # Add a download button for convenience
        csv = "\n".join(chemical_names)
        st.download_button("Download List as CSV", csv, "chemicals.csv", "text/csv")
    else:
        st.warning("No chemical names detected in this document.")
