import streamlit as st
from pypdf import PdfReader
import io
import re
import requests

# 1. Web Page Branding
st.set_page_config(page_title="Precision IUPAC Extractor", page_icon="🧪", layout="wide")
st.title("🧪 Precision Chemical IUPAC Name Extractor")
st.write("Upload a digital patent or research PDF. This engine removes English noise text, repairs formatting typos, and verifies molecular records against the Cambridge database.")

# 2. Sidebar Configuration Panel
st.sidebar.header("Configuration Panel")

# Page Boundaries
page_mode = st.sidebar.radio("Pages to Scan:", ["All Pages", "Custom Page Range"])
start_page = 40
end_page = 89

if page_mode == "Custom Page Range":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_page = st.number_input("Start Page", min_value=1, value=40, step=1)
    with col2:
        end_page = st.number_input("End Page", min_value=1, value=89, step=1)

# Example Targets Bounds
use_example_range = st.sidebar.checkbox("Filter by Example Numbers?", value=True)
comp_start = 1
comp_end = 62

if use_example_range:
    st.sidebar.write("Target Example Range:")
    c_col1, c_col2 = st.sidebar.columns(2)
    with c_col1:
        comp_start = st.number_input("From Example #", min_value=1, value=1, step=1)
    with c_col2:
        comp_end = st.number_input("To Example #", min_value=1, value=62, step=1)

# Main Dashboard Uploader
uploaded_file = st.file_uploader("Upload your digital scientific PDF file here", type=["pdf"], key="clean_uploader")

# 3. ADVANCED TEXT CORRECTION: Drops background filler text and resolves broken text columns
def clean_and_repair_iupac(text_string):
    if not text_string:
        return ""
        
    # Global drop list for common English boilerplate words that bleed into PDF extractions
    noise_words = [
        r'\bsynthesized\b', r'\bproduction\b', r'\bremarks\b', r'\bobtained\b', 
        r'\bafforded\b', r'\bmixture\b', r'\bsolution\b', r'\byield\b', 
        r'\bprepared\b', r'\bfrom\b', r'\bwith\b', r'\band\b', r'\bwas\b', r'\bas\b',
        r'\bcomparative\b', r'\bstep\b'
    ]
    
    cleaned = text_string
    for pattern in noise_words:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
    # Collapse irregular layout spacing around punctuation: "4 - ( 4 - aminophenyl )" -> "4-(4-aminophenyl)"
    cleaned = re.sub(r'\s*([-\(\)\[\]\{\},:\.\*])\s*', r'\1', cleaned)
    
    # Reconnect words split across lines/columns: "methyl amine" -> "methylamine"
    chemical_roots = ["meth", "eth", "prop", "but", "pent", "hex", "benz", "phen", "chloro", "bromo", "amino", "nitro", "hydroxy"]
    for root in chemical_roots:
        cleaned = re.sub(rf'\b({root})\s+', r'\1', cleaned, flags=re.IGNORECASE)
        
    # Standardize typography character maps
    cleaned = cleaned.replace('—', '-').replace('–', '-')  # Extended hyphens
    cleaned = cleaned.replace('{', '(').replace('}', ')')  # Layout brackets
    
    # Condense white spaces created by removals
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.strip(" .,()[]-:")

# 4. CAMBRIDGE INFRASTRUCTURE CALL
def verify_via_opsin(chemical_string):
    target_string = clean_and_repair_iupac(chemical_string)
    
    # Quickly ignore fragments that are obviously standard text labels
    if len(target_string) < 7 or target_string.lower() in ["example", "compound", "table", "structure"]:
        return False, None
        
    try:
        url = f"https://opsin.ch.cam.ac.uk/opsin/{target_string}.json"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return True, target_string
    except:
        pass
    return False, None

# 5. DATA EXTRACTION ENGINE
def execute_extraction(pdf_reader, s_page, e_page, filter_on, c_min, c_max):
    extracted_records = []
    
    # Wide catch-pattern to evaluate potential strings if number filters are off
    broad_regex = r'\b(?:[0-9,\'\"\-a-zA-Z\s\(\)\[\]]*)?(?:meth|eth|prop|but|pent|hex|hept|oct|non|dec|iso|cyclo|benz|phen|chloro|bromo|fluoro|iodo|amino|nitro|hydroxy|oxo|methyl|ethyl|propyl|butyl|phenyl|benzyl)+(?:ane|ene|yne|ol|one|al|oic\sacid|ate|ic\sacid|ide|ine|ole|azole|in|an|est|yl|oxy|µ|alpha|beta|gamma)s?\b'

    for page_idx in range(s_page, e_page):
        page_num = page_idx + 1
        text_content = pdf_reader.pages[page_idx].extract_text()
        if not text_content:
            continue
            
        lines = text_content.split('\n')
        for line in lines:
            # Capture specific header line prefixes (e.g. "Example 12")
            marker = re.search(r'\bExample\s*([0-9]+)\b', line, re.IGNORECASE)
            
            if marker and filter_on:
                try:
                    ex_num = int(marker.group(1))
                except ValueError:
                    continue
                    
                if c_min <= ex_num <= c_max:
                    # Segment lines by dual spaces or layout punctuation splits
                    chunks = re.split(r'\s{2,}|,\s|(?<=\s)(?=\()', line)
                    for chunk in chunks:
                        if any(w in chunk.lower() for w in ["stirred", "washed", "extracted", "dissolved", "purified"]):
                            continue
                            
                        is_valid, final_name = verify_via_opsin(chunk)
                        if is_valid:
                            record = {
                                "Example": ex_num,
                                "Page Number": page_num,
                                "Structure ID": f"Example {ex_num}",
                                "Corrected IUPAC Name": final_name
                            }
                            # Block redundant extractions for the same Example heading
                            if not any(r["Example"] == record["Example"] for r in extracted_records):
                                extracted_records.append(record)
                                break
                                
            elif not filter_on:
                # Fallback: General wide text scraping if target numbering is switched off
                matches = re.findall(broad_regex, line, re.IGNORECASE)
                for match in matches:
                    is_valid, final_name = verify_via_opsin(match)
                    if is_valid:
                        record = {
                            "Example": "N/A",
                            "Page Number": page_num,
                            "Structure ID": "General Match",
                            "Corrected IUPAC Name": final_name
                        }
                        if not any(r["Corrected IUPAC Name"] == record["Corrected IUPAC Name"] and r["Page Number"] == record["Page Number"] for r in extracted_records):
                            extracted_records.append(record)
                            
    # Sort the list systematically by Example number before outputting
    if filter_on:
        extracted_records.sort(key=lambda x: x["Example"])
        
    return extracted_records

# 6. RENDER SUBMISSIONS INTERFACE
if uploaded_file is not None:
    with st.spinner("Processing document data blocks..."):
        try:
            file_bytes = uploaded_file.read()
            pdf_data = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_data)
            total_pages = len(reader.pages)
            
            actual_start = max(1, start_page) - 1
            actual_end = min(total_pages, end_page)
            
            st.info(f"Scanning target text layers: Page {actual_start+1} to {actual_end}...")
            
            results = execute_extraction(reader, actual_start, actual_end, use_example_range, comp_start, comp_end)

            if results:
                st.success(f"Isolated {len(results)} verified molecular names!")
                
                # Interactive Web Dashboard Spreadsheet Matrix
                st.dataframe(results, use_container_width=True)
                
                # Data Sheet CSV Payload Builder
                csv_header = "Example,Page Number,Structure ID,Corrected IUPAC Name\n"
                csv_rows = [f'{r["Example"]},{r["Page Number"]},"{r["Structure ID"]}","{r["Corrected IUPAC Name"]}"' for r in results]
                csv_data = csv_header + "\n".join(csv_rows)
                
                st.download_button(
                    label="Download Extraction Sheet as CSV",
                    data=csv_data,
                    file_name="iupac_precision_extraction.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No definitive structures matched your target parameter settings on those pages.")
                
        except Exception as e:
            st.error(f"Processing Failure: {e}")
