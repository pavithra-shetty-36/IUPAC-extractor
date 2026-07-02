import streamlit as st
from pypdf import PdfReader
import io
import re

# 1. App Title and Description
st.title("🧪 Targeted Chemical IUPAC Name Extractor")
st.write("Upload a digital PDF to map out systematic IUPAC names linked directly to their Compound Numbers and Page Numbers.")

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
st.sidebar.write("Target Compound Range:")
c_col1, c_col2 = st.sidebar.columns(2)
with c_col1:
    comp_start = st.number_input("From Compound #", min_value=1, value=1, step=1)
with c_col2:
    comp_end = st.number_input("To Compound #", min_value=1, value=97, step=1)

# Main File Uploader
uploaded_file = st.file_uploader("Upload your digital PDF here", type=["pdf"], key="clean_uploader")

# Advanced Layout Parser to isolate Compound Numbers and their matching IUPAC names per page
def extract_compounds_with_metadata(pdf_reader, s_page, e_page, c_min, c_max):
    extracted_data = []
    
    # Rigorous IUPAC pattern matching blocks
    iupac_regex = r'\b(?:[0-9,\'\"\-a-zA-Z\s\(\)\[\]]*)?(?:meth|eth|prop|but|pent|hex|hept|oct|non|dec|iso|cyclo|benz|phen|chloro|bromo|fluoro|iodo|amino|nitro|hydroxy|oxo|methyl|ethyl|propyl|butyl|phenyl|benzyl)+(?:ane|ene|yne|ol|one|al|oic\sacid|ate|ic\sacid|ide|ine|ole|azole|in|an|est|yl|oxy|µ|alpha|beta|gamma)s?\b'

    # Loop through the document page by page to track where items live
    for page_idx in range(s_page, e_page):
        page_num = page_idx + 1
        text_content = pdf_reader.pages[page_idx].extract_text()
        
        if not text_content:
            continue
            
        # Look for explicit compound label markers (e.g., "Compound 4", "Compound (IV)", "Example 4", or standalone bold-style numbers)
        # This matches variations like: Compound 1, Compound 1a, Example 1, No. 1
        compound_markers = re.finditer(r'\b(?:Compound|Example|No\.|\b)\s*([0-9]+)[a-z]?\b', text_content, re.IGNORECASE)
        
        for marker in compound_markers:
            try:
                comp_num = int(marker.group(1))
            except ValueError:
                continue
                
            # Check if this compound matches your target user range (e.g., 1 to 97)
            if c_min <= comp_num <= c_max:
                # Isolate the text window right after the compound identifier (where the IUPAC name is typically stated)
                start_pos = marker.end()
                window_text = text_content[start_pos:start_pos + 400] # Check next 400 characters
                
                # Scan this local window for a structural IUPAC match
                chemical_matches = re.findall(iupac_regex, window_text, re.IGNORECASE)
                
                for chem in chemical_matches:
                    cleaned_chem = chem.strip(" .,()[]-:")
                    # Ensure it is a valid name string and not short text/noise
                    if len(cleaned_chem) > 6 and not cleaned_chem.isdigit() and any(char.isalpha() for char in cleaned_chem):
                        
                        # Save structural entry data
                        record = {
                            "Compound ID": f"Compound {comp_num}",
                            "IUPAC Name": cleaned_chem,
                            "Page Number": page_num
                        }
                        
                        # Prevent exact duplicates from flooding the display list
                        if record not in extracted_data:
                            extracted_data.append(record)
                            
    return extracted_data

# 3. Process the PDF file if uploaded
if uploaded_file is not None:
    with st.spinner("Extracting and matching compound layouts..."):
        try:
            file_bytes = uploaded_file.read()
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            total_pages = len(reader.pages)
            
            # Restrict page bounds securely to match actual PDF length
            actual_start = max(1, start_page) - 1
            actual_end = min(total_pages, end_page)
            
            st.info(f"Scanning Page {actual_start+1} to {actual_end} for Compounds {comp_start} through {comp_end}...")
            
            # Execute our smart page-by-page mapping script
            results = extract_compounds_with_metadata(reader, actual_start, actual_end, comp_start, comp_end)

            # 4. Display mapped results in a layout table
            if results:
                st.success(f"Successfully mapped {len(results)} compounds matching your instructions!")
                
                # Turn results into an interactive visual table matrix
                st.dataframe(results, use_container_width=True)
                
                # Create structured CSV file data
                csv_header = "Compound ID,IUPAC Name,Page Number\n"
                csv_rows = [f'"{r["Compound ID"]}","{r["IUPAC Name"]}",{r["Page Number"]}' for r in results]
                csv_data = csv_header + "\n".join(csv_rows)
                
                st.download_button(
                    label="Download Mapped Report as CSV",
                    data=csv_data,
                    file_name="chemical_compound_report.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No structural IUPAC names matching that compound number range were found on those pages. Try expanding your page or compound range filters.")
                
        except Exception as e:
            st.error(f"An error occurred during layout processing: {e}")
