import streamlit as st
from pypdf import PdfReader
import io
import re
import requests

# 1. App Title and Description
st.title("🧪 Precision Chemical IUPAC Name Extractor")
st.write("Extracts final product IUPAC names mapped to compound numbers and page numbers with auto-typo correction.")

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

# Compound Range Toggle
use_compound_range = st.sidebar.checkbox("Filter by Compound Numbers?", value=True)
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

# 3. TEXT CORRECTION ENGINE: Omit English noise words and fix PDF typo formatting
def clean_and_repair_iupac(text_string):
    if not text_string:
        return ""
        
    # List of common English filler words/noise that bleed into PDF chemical extractions
    noise_words = [
        r'\bsynthesized\b', r'\bproduction\b', r'\bremarks\b', r'\bobtained\b', 
        r'\bafforded\b', r'\bmixture\b', r'\bsolution\b', r'\byield\b', 
        r'\bprepared\b', r'\bfrom\b', r'\bwith\b', r'\band\b', r'\bwas\b', r'\bas\b'
    ]
    
    # Remove the noise words globally from the string segment
    cleaned = text_string
    for pattern in noise_words:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
    # Standardize spaces around dashes and brackets (e.g., "2- methyl" -> "2-methyl")
    cleaned = re.sub(r'\s*([-\(\)\[\]\{\},])\s*', r'\1', cleaned)
    
    # Repair broken prefixes due to rogue spaces (e.g., "methyl piperazine" -> "methylpiperazine")
    chemical_roots = ["meth", "eth", "prop", "but", "pent", "hex", "benz", "phen", "chloro", "bromo", "amino", "nitro", "hydroxy"]
    for root in chemical_roots:
        cleaned = re.sub(rf'\b({root})\s+', r'\1', cleaned, flags=re.IGNORECASE)
        
    # Replace layout bad characters
    cleaned = cleaned.replace('—', '-').replace('–', '-') # Standardize dashes
    cleaned = cleaned.replace('{', '(').replace('}', ')') # Standardize brackets
    
    # Condense double spaces caused by removed words
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.strip(" .,()[]-:")

# 4. CAMBRIDGE VALIDATION API LAYER
def verify_via_opsin(chemical_string):
    # Run structural repair first
    target_string = clean_and_repair_iupac(chemical_string)
    
    # Filter out empty or obviously non-chemical fragments
    if len(target_string) < 7 or target_string.lower() in ["a", "the", "compound", "example"]:
        return False, None
        
    try:
        # Check against Cambridge structure database
        url = f"https://opsin.ch.cam.ac.uk/opsin/{target_string}.json"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return True, target_string
    except:
        pass
    return False, None

# 5. CORE PARSING MATRIX
def execute_extraction(pdf_reader, s_page, e_page, filter_on, c_min, c_max):
    extracted_records = []
    
    # Broad catch pattern to isolate chemical candidate chunks when scanning freely
    broad_regex = r'\b(?:[0-9,\'\"\-a-zA-Z\s\(\)\[\]]*)?(?:meth|eth|prop|but|pent|hex|hept|oct|non|dec|iso|cyclo|benz|phen|chloro|bromo|fluoro|iodo|amino|nitro|hydroxy|oxo|methyl|ethyl|propyl|butyl|phenyl|benzyl)+(?:ane|ene|yne|ol|one|al|oic\sacid|ate|ic\sacid|ide|ine|ole|azole|in|an|est|yl|oxy|µ|alpha|beta|gamma)s?\b'

    for page_idx in range(s_page, e_page):
        page_num = page_idx + 1
        text_content = pdf_reader.pages[page_idx].extract_text()
        if not text_content:
            continue
            
        lines = text_content.split('\n')
        for line in lines:
            # Look for structured headers like "Compound 4" or "Example 4"
            marker = re.search(r'\b(?:Compound|Example|No\.|\b)\s*([0-9]+)\b', line, re.IGNORECASE)
            
            if marker and filter_on:
                try:
                    comp_num = int(marker.group(1))
                except ValueError:
                    continue
                    
                if c_min <= comp_num <= c_max:
                    # Break targeted compound layout lines by spacing structures
                    chunks = re.split(r'\s{2,}|,\s|(?<=\s)(?=\()', line)
                    for chunk in chunks:
                        # Drop words immediately associated with intermediate workflow descriptions
                        if any(w in chunk.lower() for w in ["stirred", "washed", "extracted", "dissolved"]):
                            continue
                            
                        is_valid, final_name = verify_via_opsin(chunk)
                        if is_valid:
                            record = {
                                "Compound ID": f"Compound {comp_num}",
                                "Final IUPAC Name": final_name,
                                "Page Number": page_num
                            }
                            if not any(r["Compound ID"] == record["Compound ID"] for r in extracted_records):
                                extracted_records.append(record)
                                break
                                
            elif not filter_on:
                # General Mode: Pull matching raw chemical components passing validation filters
                matches = re.findall(broad_regex, line, re.IGNORECASE)
                for match in matches:
                    is_valid, final_name = verify_via_opsin(match)
                    if is_valid:
                        record = {
                            "Compound ID": "General Product Match",
                            "Final IUPAC Name": final_name,
                            "Page Number": page_num
                        }
                        if not any(r["Final IUPAC Name"] == record["Final IUPAC Name"] and r["Page Number"] == record["Page Number"] for r in extracted_records):
                            extracted_records.append(record)
                            
    return extracted_records

# 6. RENDER DATA MANAGEMENT
if uploaded_file is not None:
    with st.spinner("Extracting, correcting, and validating target IUPAC data structures..."):
        try:
            file_bytes = uploaded_file.read()
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            total_pages = len(reader.pages)
            
            actual_start = max(1, start_page) - 1
            actual_end = min(total_pages, end_page)
            
            st.info(f"Scanning targeted text layout: Page {actual_start+1} to {actual_end}...")
            
            results = execute_extraction(reader, actual_start, actual_end, use_compound_range, comp_start, comp_end)

            if results:
                st.success(f"Isolated {len(results)} verified IUPAC chemical structures!")
                st.dataframe(results, use_container_width=True)
                
                csv_header = "Compound ID,Final IUPAC Name,Page Number\n"
                csv_rows = [f'"{r["Compound ID"]}","{r["Final IUPAC Name"]}",{r["Page Number"]}' for r in results]
                csv_data = csv_header + "\n".join(csv_rows)
                
                st.download_button(
                    label="Download Report as CSV",
                    data=csv_data,
                    file_name="iupac_precision_report.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No target IUPAC configurations passed extraction and validation tests with current parameters.")
                
        except Exception as e:
            st.error(f"Processing Matrix Exception occurred: {e}")
