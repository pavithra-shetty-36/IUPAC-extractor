import streamlit as st
from pypdf import PdfReader
import io
import re
import requests

# 1. App Title and Description
st.title("🧪 Final Chemical Compound IUPAC Extractor")
st.write("This version automatically repairs minor PDF text extraction typos before validating with Cambridge OPSIN.")

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

# New Auto-Correction Engine to fix minor PDF typos
def repair_iupac_typos(text_string):
    # 1. Strip accidental spaces around brackets and hyphens (e.g., "2- amino" -> "2-amino")
    text_string = re.sub(r'\s*([-\(\)\[\]\{\},])\s*', r'\1', text_string)
    
    # 2. Fix broken multi-word segments for common chemical roots (e.g., "methyl benzene" -> "methylbenzene")
    chemical_roots = ["meth", "eth", "prop", "but", "pent", "hex", "benz", "phen", "chloro", "bromo", "amino", "nitro", "hydroxy"]
    for root in chemical_roots:
        text_string = re.sub(rf'\b({root})\s+', r'\1', text_string, flags=re.IGNORECASE)

    # 3. Standardize hyphens (replace em-dashes or en-dashes with standard hyphens)
    text_string = text_string.replace('—', '-').replace('–', '-')
    
    # 4. Standardize curly brackets back to normal brackets if corrupted
    text_string = text_string.replace('{', '(').replace('}', ')')
    
    return text_string.strip(" .,()[]-:")

# Checks if a string is a REAL IUPAC name using Cambridge OPSIN
def is_valid_iupac(text_string):
    # Run the correction engine first!
    clean_string = repair_iupac_typos(text_string)
    
    # Fast filtering of obvious non-chemical text noise
    if len(clean_string) < 7 or any(phrase in clean_string.lower() for phrase in ["mixture of", "by replacing", "added to", "solution of", "prepared from"]):
        return False, None
        
    try:
        # Query the official OPSIN web API
        url = f"https://opsin.ch.cam.ac.uk/opsin/{clean_string}.json"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return True, clean_string # Success!
    except:
        pass
    return False, None

# Main text splitter and parser
def extract_verified_final_compounds(pdf_reader, s_page, e_page, c_min, c_max):
    extracted_data = []

    for page_idx in range(s_page, e_page):
        page_num = page_idx + 1
        text_content = pdf_reader.pages[page_idx].extract_text()
        
        if not text_content:
            continue
            
        lines = text_content.split('\n')
        for line in lines:
            marker = re.search(r'\b(?:Compound|Example|No\.|\b)\s*([0-9]+)\b', line, re.IGNORECASE)
            if marker:
                try:
                    comp_num = int(marker.group(1))
                except ValueError:
                    continue
                
                if c_min <= comp_num <= c_max:
                    # Split the line cleanly to target name blocks
                    potential_blocks = re.split(r'\s{2,}|,\s|(?<=\s)(?=\()', line)
                    
                    for block in potential_blocks:
                        if any(k in block.lower() for k in ["stirred", "mixture", "replacing", "reaction", "added", "yield"]):
                            continue
                            
                        is_chemical, verified_name = is_valid_iupac(block)
                        if is_chemical:
                            record = {
                                "Compound ID": f"Compound {comp_num}",
                                "Final IUPAC Name": verified_name,
                                "Page Number": page_num
                            }
                            if not any(r["Compound ID"] == record["Compound ID"] for r in extracted_data):
                                extracted_data.append(record)
                                break 
                                
    return extracted_data

# 3. Process the PDF file if uploaded
if uploaded_file is not None:
    with st.spinner("Extracting text, repairing typos, and verifying with OPSIN..."):
        try:
            file_bytes = uploaded_file.read()
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            total_pages = len(reader.pages)
            
            actual_start = max(1, start_page) - 1
            actual_end = min(total_pages, end_page)
            
            st.info(f"Scanning Page {actual_start+1} to {actual_end}...")
            
            results = extract_verified_final_compounds(reader, actual_start, actual_end, comp_start, comp_end)

            if results:
                st.success(f"Successfully isolated {len(results)} verified final compounds!")
                st.dataframe(results, use_container_width=True)
                
                csv_header = "Compound ID,Final IUPAC Name,Page Number\n"
                csv_rows = [f'"{r["Compound ID"]}","{r["Final IUPAC Name"]}",{r["Page Number"]}' for r in results]
                csv_data = csv_header + "\n".join(csv_rows)
                
                st.download_button(
                    label="Download Verified Report as CSV",
                    data=csv_data,
                    file_name="repaired_final_compounds.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No verified IUPAC titles matching that compound range passed chemical validation on these pages.")
                
        except Exception as e:
            st.error(f"An error occurred during layout processing: {e}")
