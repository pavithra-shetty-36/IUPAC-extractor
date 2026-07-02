import streamlit as st
from pypdf import PdfReader
import io
import re
import requests

# 1. App Title and Description
st.title("🧪 Verified Final Chemical Compound IUPAC Extractor")
st.write("This version uses the Cambridge OPSIN engine to validate real chemical names and filter out random text noise.")

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

# Function that checks if a string is a REAL IUPAC name using Cambridge OPSIN
def is_valid_iupac(text_string):
    # Clean up common text garbage around the word
    clean_string = text_string.strip(" .,()[]-:")
    
    # Fast filtering of obvious non-chemical text noise
    if len(clean_string) < 7 or any(phrase in clean_string.lower() for phrase in ["mixture of", "by replacing", "added to", "solution of", "prepared from"]):
        return False, None
        
    try:
        # Query the official OPSIN web API (free, instant, no-key required)
        url = f"https://opsin.ch.cam.ac.uk/opsin/{clean_string}.json"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return True, clean_string # It's a verified IUPAC name!
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
            
        # Regex to find where compound headings are declared (e.g. "Compound 1", "Example 4")
        # Captures lines containing the compound marker
        lines = text_content.split('\n')
        for line in lines:
            marker = re.search(r'\b(?:Compound|Example|No\.|\b)\s*([0-9]+)\b', line, re.IGNORECASE)
            if marker:
                try:
                    comp_num = int(marker.group(1))
                except ValueError:
                    continue
                
                # Check if it falls in your targeted range
                if c_min <= comp_num <= c_max:
                    # Final compound names are almost always in the same header line or right below it
                    # Split the line by spaces or commas to check individual large word blocks
                    potential_blocks = re.split(r'\s{2,}|,\s|(?<=\s)(?=\()', line)
                    
                    for block in potential_blocks:
                        # Skip text chunks that contain reaction method keywords
                        if any(k in block.lower() for k in ["stirred", "mixture", "replacing", "reaction", "added", "yield"]):
                            continue
                            
                        # Double-check against the Cambridge chemical structure parser
                        is_chemical, verified_name = is_valid_iupac(block)
                        if is_chemical:
                            record = {
                                "Compound ID": f"Compound {comp_num}",
                                "Final IUPAC Name": verified_name,
                                "Page Number": page_num
                            }
                            # Keep only one primary validated compound entry per number
                            if not any(r["Compound ID"] == record["Compound ID"] for r in extracted_data):
                                extracted_data.append(record)
                                break # Found the main title final compound, stop looking in this line
                                
    return extracted_data

# 3. Process the PDF file if uploaded
if uploaded_file is not None:
    with st.spinner("Extracting text and verifying real IUPAC structures via OPSIN..."):
        try:
            file_bytes = uploaded_file.read()
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            total_pages = len(reader.pages)
            
            actual_start = max(1, start_page) - 1
            actual_end = min(total_pages, end_page)
            
            st.info(f"Scanning Page {actual_start+1} to {actual_end}...")
            
            results = extract_verified_final_compounds(reader, actual_start, actual_end, comp_start, comp_end)

            # 4. Display mapped results in a layout table
            if results:
                st.success(f"Successfully isolated {len(results)} verified final compounds!")
                st.dataframe(results, use_container_width=True)
                
                csv_header = "Compound ID,Final IUPAC Name,Page Number\n"
                csv_rows = [f'"{r["Compound ID"]}","{r["Final IUPAC Name"]}",{r["Page Number"]}' for r in results]
                csv_data = csv_header + "\n".join(csv_rows)
                
                st.download_button(
                    label="Download Verified Report as CSV",
                    data=csv_data,
                    file_name="verified_final_compounds.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No verified IUPAC titles matching that compound range passed chemical validation on these pages.")
                
        except Exception as e:
            st.error(f"An error occurred during layout processing: {e}")
