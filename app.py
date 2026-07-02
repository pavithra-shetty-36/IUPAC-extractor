import streamlit as st
from pypdf import PdfReader
import io
import re

# 1. App Title and Description
st.title("🧪 Custom Chemical IUPAC Name Extractor")
st.write("Upload a digital PDF and use the sidebar settings to target specific pages or compound ranges.")

# 2. Sidebar Configuration Controls
st.sidebar.header("Filter Options")

# Page Range Selector
page_mode = st.sidebar.radio("Pages to Scan:", ["All Pages", "Custom Page Range"])
start_page = 1
end_page = 999

if page_mode == "Custom Page Range":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_page = st.number_input("Start Page", min_value=1, value=1, step=1)
    with col2:
        end_page = st.number_input("End Page", min_value=1, value=5, step=1)

# Compound Filter Settings
enable_compound_filter = st.sidebar.checkbox("Filter by Compound Numbers", value=False)
comp_start = 1
comp_end = 97

if enable_compound_filter:
    st.sidebar.write("Specify Compound range (e.g., Compound 1 to 97):")
    c_col1, c_col2 = st.sidebar.columns(2)
    with c_col1:
        comp_start = st.number_input("From Compound #", min_value=1, value=1, step=1)
    with c_col2:
        comp_end = st.number_input("To Compound #", min_value=1, value=97, step=1)

# Main File Uploader
uploaded_file = st.file_uploader("Upload your digital PDF here", type=["pdf"], key="clean_uploader")

# Comprehensive pattern match for systematic chemical nomenclature
def extract_iupac_patterns(text, enable_filter, c_min, c_max):
    chemical_regex = r'\b(?:[0-9,\'\"\-a-zA-Z\s\(\)\[\]]*)?(?:meth|eth|prop|but|pent|hex|hept|oct|non|dec|iso|cyclo|benz|phen|chloro|bromo|fluoro|iodo|amino|nitro|hydroxy|oxo|methyl|ethyl|propyl|butyl|phenyl|benzyl)+(?:ane|ene|yne|ol|one|al|oic\sacid|ate|ic\sacid|ide|ine|ole|azole|in|an|est|yl|oxy|µ|alpha|beta|gamma)s?\b'
    matches = re.findall(chemical_regex, text, re.IGNORECASE)
    
    cleaned_names = []
    for match in matches:
        cleaned = match.strip(" .,()[]-")
        if len(cleaned) > 4 and not cleaned.isdigit() and any(char.isalpha() for char in cleaned):
            
            # If the user enabled compound number filtering, look for numbers near the match
            if enable_filter:
                # This checks if the text string contains numbers matching your specified range
                found_numbers = [int(s) for s in re.findall(r'\b\d+\b', cleaned)]
                if found_numbers:
                    # If it has numbers, ensure at least one falls inside your range
                    if not any(c_min <= num <= c_max for num in found_numbers):
                        continue # Skip this compound if it's out of range
                        
            cleaned_names.append(cleaned)
            
    return list(set(cleaned_names))

# 3. Process the PDF file if uploaded
if uploaded_file is not None:
    with st.spinner("Reading targeted PDF pages..."):
        try:
            raw_text = ""
            file_bytes = uploaded_file.read()
            
            # Extract text from digital layers
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            total_pages = len(reader.pages)
            
            # Adjust ranges securely based on actual PDF length
            actual_start = max(1, start_page) - 1
            actual_end = min(total_pages, end_page)
            
            if page_mode == "Custom Page Range":
                st.info(f"Scanning targeted range: Page {actual_start+1} to {actual_end} (Total document pages: {total_pages})")
            
            # Loop through only the requested pages
            for page_num in range(actual_start, actual_end):
                text_content = reader.pages[page_num].extract_text()
                if text_content:
                    raw_text += text_content + "\n"
            
            # 4. Check if text extraction worked
            if not raw_text.strip():
                st.error("Could not extract text from the selected pages. Ensure they contain actual digital text layers, or adjust your page range configuration.")
            else:
                st.info("Filtering and sorting targeted chemical terms...")
                chemical_names = extract_iupac_patterns(raw_text, enable_compound_filter, comp_start, comp_end)

                # 5. Output results
                if chemical_names:
                    st.success(f"Found {len(chemical_names)} unique chemical names matching your settings!")
                    st.write("### Extracted IUPAC / Chemical Names:")
                    
                    for name in chemical_names:
                        st.write(f"- {name}")
                        
                    csv = "\n".join(chemical_names)
                    st.download_button("Download Filtered List as CSV", csv, "filtered_chemicals.csv", "text/csv")
                else:
                    st.warning("No chemical names matching your targeted rules and compound ranges were detected in these pages.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
