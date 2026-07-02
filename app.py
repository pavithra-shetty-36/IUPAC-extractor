import streamlit as st
from pypdf import PdfReader
import io
import re
import requests

# 1. App Title and Description
st.title("🧪 Flexible Chemical IUPAC Name Extractor")
st.write("Upload a digital PDF. Works with or without specific compound numbering systems.")

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

# Compound Filter Toggle (The new adaptive feature!)
use_compound_range = st.sidebar.checkbox("Filter by Compound Numbers?", value=False)
comp_start = 1
comp_end = 97

if use_compound_range:
    st.sidebar.write("Target Compound Range:")
    c_col1, c_col2 = st.sidebar.columns(2)
    with c_col1:
        comp_start = st.number_input("From Compound #", min_value=1, value=1, step=1)
    with c_col2:
        comp_end = st.number_input("To Compound #", min_value=1, value=97, step=1)

# Main File Uploader
uploaded_file = st.file_uploader("Upload your digital PDF here", type=["pdf"], key="clean_uploader")

# Auto-Correction Engine to fix minor PDF typos
def repair_iupac_typos(text_string):
    text_string = re.sub(r'\s*([-\(\)\[\]\{\},])\s*', r'\1', text_string)
    chemical_roots = ["meth", "eth", "prop", "but", "pent", "hex", "benz", "phen", "chloro", "bromo", "amino", "nitro", "hydroxy"]
    for root in chemical_roots:
        text_string = re.sub(rf'\b({root})\s+', r'\1', text_string, flags=re.IGNORECASE)
    text_string = text_string.replace('—', '-').replace('–', '-')
    text_string = text_string.replace('{', '(').replace('}', ')')
    return text_string.strip(" .,()[]-:")

# Checks if a string is a REAL IUPAC name using Cambridge OPSIN
def is_valid_iupac(text_string):
    clean_string = repair_iupac_typos(text_string)
    
    if len(clean_string) < 7 or any(phrase in clean_string.lower() for phrase in ["mixture of", "by replacing", "added to", "solution of", "prepared from", "washed with", "extracted with"]):
        return False, None
        
    try:
        url = f"https://opsin.ch.cam.ac.uk/opsin/{clean_string}.json"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return True, clean_string 
    except:
        pass
    return False, None

# Fully adaptive extractor logic
def extract_adaptive_iupac(pdf_reader, s_page, e_page, use_filter, c_min, c_max):
    extracted_data = []
    
    # Generic wide regex to catch potential chemical candidates when no compound numbers exist
    broad_chemical_regex = r'\b(?:[0-9,\'\"\-a-zA-Z\s\(\)\[\]]*)?(?:meth|eth|prop|but|pent|hex|hept|oct|non|dec|iso|cyclo|benz|phen|chloro|bromo|fluoro|iodo|amino|nitro|hydroxy|oxo|methyl|ethyl|propyl|butyl|phenyl|benzyl)+(?:ane|ene|yne|ol|one|al|oic\sacid|ate|ic\sacid|ide|ine|ole|azole|in|an|est|yl|oxy|µ|alpha|beta|gamma)s?\b'

    for page_idx in range(s_page, e_page):
        page_num = page_idx + 1
        text_content = pdf_reader.pages[page_idx].extract_text()
        
        if not text_content:
            continue
            
        # MODE A: Strict Compound Number Range Filtering
        if use_filter:
            lines = text_content.split('\n')
            for line in lines:
                marker = re.search(r'\b(?:Compound|Example|No\.|\b)\s*([0-9]+)\b', line, re.IGNORECASE)
                if marker:
                    try:
                        comp_num = int(marker.group(1))
                    except ValueError:
                        continue
                    
                    if c_min <= comp_num <= c_max:
                        potential_blocks = re.split(r'\s{2,}|,\s|(?<=\s)(?=\()', line)
                        for block in potential_blocks:
                            if any(k in block.lower() for k in ["stirred", "mixture", "replacing", "reaction", "added"]):
                                continue
                            is_chemical, verified_name = is_valid_iupac(block)
                            if is_chemical:
                                record = {
                                    "ID / Label": f"Compound {comp_num}",
                                    "Verified IUPAC Name": verified_name,
                                    "Page Number": page_num
                                }
                                if not any(r["ID / Label"] == record["ID / Label"] for r in extracted_data):
                                    extracted_data.append(record)
                                    break 

        # MODE B: General Extraction (No compound number matching)
        else:
            # Find all words matching chemical patterns anywhere on the page
            found_words = re.findall(broad_chemical_regex, text_content, re.IGNORECASE)
            for word in found_words:
                is_chemical, verified_name = is_valid_iupac(word)
                if is_chemical:
                    record = {
                        "ID / Label": "General Text Match",
                        "Verified IUPAC Name": verified_name,
                        "Page Number": page_num
                    }
                    # Prevent adding identical chemical structures found on the same page
                    if not any(r["Verified IUPAC Name"] == record["Verified IUPAC Name"] and r["Page Number"] == record["Page Number"] for r in extracted_data):
                        extracted_data.append(record)
                                
    return extracted_data

# 3. Process the PDF file if uploaded
if uploaded_file is not None:
    with st.spinner("Extracting and verifying IUPAC chemical records..."):
        try:
            file_bytes = uploaded_file.read()
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            total_pages = len(reader.pages)
            
            actual_start = max(1, start_page) - 1
            actual_end = min(total_pages, end_page)
            
            st.info(f"Scanning Page {actual_start+1} to {actual_end}...")
            
            results = extract_adaptive_iupac(reader, actual_start, actual_end, use_compound_range, comp_start, comp_end)

            if results:
                st.success(f"Successfully isolated {len(results)} verified IUPAC chemical structures!")
                st.dataframe(results, use_container_width=True)
                
                csv_header = "ID / Label,Verified IUPAC Name,Page Number\n"
                csv_rows = [f'"{r["ID / Label"]}","{r["Verified IUPAC Name"]}",{r["Page Number"]}' for r in results]
                csv_data = csv_header + "\n".join(csv_rows)
                
                st.download_button(
                    label="Download Extraction Report as CSV",
                    data=csv_data,
                    file_name="iupac_extraction_report.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No strings passed the Cambridge chemical structure validation on these pages with your current settings.")
                
        except Exception as e:
            st.error(f"An error occurred during extraction processing: {e}")
