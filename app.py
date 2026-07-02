import streamlit as st
from pypdf import PdfReader
import io
import re

# 1. App Title and Description
st.title("🧪 Final Chemical Compound IUPAC Extractor")
st.write("Upload a digital PDF to extract ONLY the final target compound IUPAC names linked to your specified compound numbers.")

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

# Advanced parsing to extract ONLY the final compound name
def extract_final_compounds(pdf_reader, s_page, e_page, c_min, c_max):
    extracted_data = []
    
    # Core IUPAC regex token
    iupac_regex = r'\b(?:[0-9,\'\"\-a-zA-Z\s\(\)\[\]]*)?(?:meth|eth|prop|but|pent|hex|hept|oct|non|dec|iso|cyclo|benz|phen|chloro|bromo|fluoro|iodo|amino|nitro|hydroxy|oxo|methyl|ethyl|propyl|butyl|phenyl|benzyl)+(?:ane|ene|yne|ol|one|al|oic\sacid|ate|ic\sacid|ide|ine|ole|azole|in|an|est|yl|oxy|µ|alpha|beta|gamma)s?\b'

    for page_idx in range(s_page, e_page):
        page_num = page_idx + 1
        text_content = pdf_reader.pages[page_idx].extract_text()
        
        if not text_content:
            continue
            
        # Search for exact compound declarations (e.g., "Compound 1" or standalone "1" at start of line/paragraph)
        compound_markers = re.finditer(r'\b(?:Compound|Example|No\.|\b)\s*([0-9]+)[a-zA-Z]?\b', text_content, re.IGNORECASE)
        
        for marker in compound_markers:
            try:
                comp_num = int(marker.group(1))
            except ValueError:
                continue
                
            if c_min <= comp_num <= c_max:
                start_pos = marker.end()
                
                # Squeeze the window down significantly (first 150 chars) to get ONLY the heading title name
                # Final IUPAC names are usually right next to the compound header number before the text describes the method
                window_text = text_content[start_pos:start_pos + 150]
                
                # Check if common reaction words (used for intermediates/reagents) are in this block. 
                # If they are, it means we stumbled into the experiment text, not the main title.
                if any(word in window_text.lower() for word in ["added to", "dissolved in", "stirred for", "washed with"]):
                    continue

                chemical_matches = re.findall(iupac_regex, window_text, re.IGNORECASE)
                
                if chemical_matches:
                    # Select ONLY the very first chemical match found immediately after the number
                    # This prevents capturing intermediates listed later in the paragraph sentences
                    primary_chem = chemical_matches[0]
                    cleaned_chem = primary_chem.strip(" .,()[]-:")
                    
                    if len(cleaned_chem) > 6 and not cleaned_chem.isdigit() and any(char.isalpha() for char in cleaned_chem):
                        record = {
                            "Compound ID": f"Compound {comp_num}",
                            "Final IUPAC Name": cleaned_chem,
                            "Page Number": page_num
                        }
                        
                        # Update or add record (ensuring one primary IUPAC per compound number)
                        if not any(r["Compound ID"] == record["Compound ID"] for r in extracted_data):
                            extracted_data.append(record)
                            
    return extracted_data

# 3. Process the PDF file if uploaded
if uploaded_file is not None:
    with st.spinner("Isolating final compound names..."):
        try:
            file_bytes = uploaded_file.read()
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            total_pages = len(reader.pages)
            
            actual_start = max(1, start_page) - 1
            actual_end = min(total_pages, end_page)
            
            st.info(f"Scanning Page {actual_start+1} to {actual_end}...")
            
            results = extract_final_compounds(reader, actual_start, actual_end, comp_start, comp_end)

            # 4. Display mapped results in a layout table
            if results:
                st.success(f"Successfully isolated {len(results)} final compounds!")
                st.dataframe(results, use_container_width=True)
                
                csv_header = "Compound ID,Final IUPAC Name,Page Number\n"
                csv_rows = [f'"{r["Compound ID"]}","{r["Final IUPAC Name"]}",{r["Page Number"]}' for r in results]
                csv_data = csv_header + "\n".join(csv_rows)
                
                st.download_button(
                    label="Download Final Compound Report as CSV",
                    data=csv_data,
                    file_name="final_compounds_only.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No definitive final compound headings matching that range were found. Try adjusting your target constraints.")
                
        except Exception as e:
            st.error(f"An error occurred during layout processing: {e}")
