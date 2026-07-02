import streamlit as st
from transformers import pipeline

# 1. App Title and Description
st.title("🧪 Chemical IUPAC Name Extractor")
st.write("Paste your scientific text or paper abstract below, and the AI will extract the IUPAC chemical names.")

# 2. Text Input Area (Bypasses the buggy file uploader)
raw_text = st.text_area("Paste your text here:", height=300, placeholder="Example: The synthesis of 2-(acetyloxy)benzoic acid was successful...")

# Load the specialized Chemical AI Model
@st.cache_resource
def load_model():
    return pipeline("ner", model="samuel95/bert-base-chemical", aggregation_strategy="simple")

# 3. Process button
if st.button("Extract Chemical Names"):
    if raw_text.strip() == "":
        st.warning("Please paste some text first!")
    else:
        with st.spinner("Analyzing text for chemical names..."):
            nlp = load_model()
            ner_results = nlp(raw_text)
            
            # Clean up and extract unique chemical names found
            chemical_names = list(set([result['word'] for result in ner_results]))

        # 4. Display Results
        if chemical_names:
            st.success(f"Found {len(chemical_names)} chemical names!")
            st.write("### Extracted IUPAC / Chemical Names:")
            
            for name in chemical_names:
                st.write(f"- {name}")
                
            # Add a download button for convenience
            csv = "\n".join(chemical_names)
            st.download_button("Download List as CSV", csv, "chemicals.csv", "text/csv")
        else:
            st.warning("No chemical names detected in this text.")
