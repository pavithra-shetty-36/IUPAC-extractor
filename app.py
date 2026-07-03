import streamlit as st
from pypdf import PdfReader
import io
import re
import json
from google import genai
from google.genai import types

# 1. Web Page Branding
st.set_page_config(page_title="Dynamic AI IUPAC Extractor", page_icon="🧪", layout="wide")
st.title("🧪 Custom Dynamic AI Chemical IUPAC Extractor")
st.write("Upload any digital PDF. Provide your API key and target configurations below to process via Gemini AI.")

# 2. Key & Range Inputs directly on the Page Interface
st.subheader("1. API Authentication & Settings")
col_api, col_pg, col_cmp = st.columns([2, 1, 1])

with col_api:
    api_key = st.text_input("Enter your Gemini API Key:", type="password", help="Get a free key at https://aistudio.google.com/")

with col_pg:
    page_input = st.text_input(
        "Specify Page(s) to Scan:", 
        value="40-89", 
        help="Examples: '40-89' for a range, '42' for a single page, or leave blank to scan the whole document."
    )

with col_cmp:
    compound_input = st.text_input(
        "Specify Target Compound/Example Range:", 
        value="1-62", 
        help="Examples: '1-62' for a range, or '5' for a single structure target."
    )

# Main Dashboard Uploader
st.subheader("2. Upload Document")
uploaded_file = st.file_uploader("Upload your digital patent or research PDF file here", type=["pdf"])

# Helper function to parse user text inputs (e.g., "40-89" -> start=40, end=89)
def parse_custom_range(input_str, default_start, default_end):
    if not input_str.strip():
        return default_start, default_end
    # Check for hyphen ranges like "40-89"
    range_match = re.match(r'^(\d+)\s*-\s*(\d+)$', input_str.strip())
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    # Check for single values like "42"
    single_match = re.match(r'^(\d+)$', input_str.strip())
    if single_match:
        val = int(single_match.group(1))
        return val, val
    return default_start, default_end

# 3. CORE AI PROCESSING FUNCTION
def analyze_page_with_ai(client, page_text, page_num, c_min, c_max):
    prompt = f"""
    You are an expert chemical text-mining assistant. Your task is to extract chemical names from patent text.
    
    Instructions:
    1. Scan the text for explicit mentions of "Example X" or "Compound X" (where X is a number).
    2. Identify ONLY the MAIN FINAL PRODUCT synthesized for that specific Example/Compound block. Do NOT extract intermediate reagents or solvents.
    3. The text might contain bad spacing, broken words, or typo brackets due to PDF extraction (e.g., "N -( 4 - aminophenyl )" or "pyrimidin - 2 - amine"). 
       You MUST automatically repair these typos to form perfect, standard, continuous IUPAC nomenclature.
    4. Ignore general English sentences, filler phrases, or reaction notes.
    5. Only return entries where the structure number falls between {c_min} and {c_max} (inclusive).
    
    Text content from Page {page_num}:
    \"\"\"
    {page_text}
    \"\"\"
    
    You must output your answer STRICTLY as a JSON list of objects matching this exact structure, with no extra formatting, markdown tags, or explanation:
    [
      {{"Structure ID": "Example X or Compound X", "Corrected IUPAC Name": "actual_cleaned_iupac_name_here", "Page Number": {page_num}}}
    ]
    If no relevant entries are found, return an empty list: []
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        st.warning(f"AI could not parse page {page_num}: {e}")
        return []

# 4. RENDER AND EXECUTION
if uploaded_file is not None:
    if not api_key.strip():
        st.error("🔑 Please enter your Gemini API Key in the box above to start the AI extraction process.")
    else:
        with st.spinner("Reading PDF structure..."):
            try:
                # Read total document shape
                file_bytes = uploaded_file.read()
                pdf_data = io.BytesIO(file_bytes)
                reader = PdfReader(pdf_data)
                total_pages = len(reader.pages)
                
                # Dynamically parse custom bounds
                parsed_start_page, parsed_end_page = parse_custom_range(page_input, 1, total_pages)
                actual_start = max(1, parsed_start_page) - 1
                actual_end = min(total_pages, parsed_end_page)
                
                comp_start, comp_end = parse_custom_range(compound_input, 1, 9999)
                
                st.info(f"🤖 AI engine scheduled to scan Pages {actual_start+1} to {actual_end} targeting Compounds/Examples {comp_start} to {comp_end}...")
                
                # Initialize Gemini client using the key typed directly into the page
                client = genai.Client(api_key=api_key.strip())
                
                all_results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_to_scan = (actual_end - actual_start) if (actual_end > actual_start) else 1
                
                # Execute extraction page by page
                for idx, page_idx in enumerate(range(actual_start, actual_end)):
                    page_num = page_idx + 1
                    status_text.text(f"Analyzing page {page_num} of {total_pages} with AI...")
                    
                    text_content = reader.pages[page_idx].extract_text()
                    if text_content and text_content.strip():
                        page_data = analyze_page_with_ai(client, text_content, page_num, comp_start, comp_end)
                        if page_data:
                            all_results.extend(page_data)
                    
                    progress_bar.progress(min(1.0, (idx + 1) / total_to_scan))
                
                status_text.text("AI extraction process complete!")
                
                # Filter out accidental duplicate parses
                unique_results = []
                seen_ids = set()
                for item in all_results:
                    struct_id = item.get("Structure ID", "")
                    if struct_id not in seen_ids:
                        seen_ids.add(struct_id)
                        unique_results.append(item)
                
                # Render Results
                if unique_results:
                    st.success(f"Successfully compiled {len(unique_results)} chemical structures matching your input specifications!")
                    st.dataframe(unique_results, use_container_width=True)
                    
                    # CSV Spreadsheet Builder
                    csv_header = "Structure ID,Corrected IUPAC Name,Page Number\n"
                    csv_rows = [f'"{r.get("Structure ID","")}","{r.get("Corrected IUPAC Name","")}",{r.get("Page Number",0)}' for r in unique_results]
                    csv_data = csv_header + "\n".join(csv_rows)
                    
                    st.download_button(
                        label="Download Extraction Data Sheet as CSV",
                        data=csv_data,
                        file_name="custom_ai_iupac_report.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No definitive chemical structures matching your target text queries were discovered on those pages.")
                    
            except Exception as e:
                st.error(f"Execution Error: {e}")
