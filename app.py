import streamlit as st
from pypdf import PdfReader
import io
import re
import json
from google import genai
from google.genai import types

# 1. Web Page Branding
st.set_page_config(page_title="AI IUPAC Extractor", page_icon="🧪", layout="wide")
st.title("🧪 AI-Powered Chemical IUPAC Extractor")
st.write("This app uses Google Gemini AI to intelligently read pages, bypass text typos, and cleanly isolate final product IUPAC names.")

# 2. Sidebar Configuration Panel
st.sidebar.header("1. API Authentication")
api_key = st.sidebar.text_input("Enter your Gemini API Key:", type="password")
st.sidebar.caption("Get a free key at https://aistudio.google.com/")

st.sidebar.header("2. Filter Options")
page_mode = st.sidebar.radio("Pages to Scan:", ["All Pages", "Custom Page Range"])
start_page = 40
end_page = 89

if page_mode == "Custom Page Range":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_page = st.number_input("Start Page", min_value=1, value=40, step=1)
    with col2:
        end_page = st.number_input("End Page", min_value=1, value=89, step=1)

st.sidebar.write("Target Example Range:")
c_col1, c_col2 = st.sidebar.columns(2)
with c_col1:
    comp_start = st.number_input("From Example #", min_value=1, value=1, step=1)
with c_col2:
    comp_end = st.number_input("To Example #", min_value=1, value=62, step=1)

# Main File Uploader
uploaded_file = st.file_uploader("Upload your digital patent or research PDF file here", type=["pdf"])

# 3. CORE AI PROCESSING FUNCTION
def analyze_page_with_ai(client, page_text, page_num, c_min, c_max):
    """
    Sends the raw page text to Gemini and asks it to extract only the target final compounds
    in a clean JSON layout, fixing text typos natively.
    """
    prompt = f"""
    You are an expert chemical text-mining assistant. Your task is to extract chemical names from patent text.
    
    Instructions:
    1. Scan the text for explicit mentions of "Example X" (where X is a number).
    2. Identify ONLY the MAIN FINAL PRODUCT synthesized for that specific Example. Do NOT extract intermediate reagents or solvents.
    3. The text might contain bad spacing, broken words, or typo brackets due to PDF extraction (e.g., "N -( 4 - aminophenyl )" or "pyrimidin - 2 - amine"). 
       You MUST automatically repair these typos to form perfect, standard, continuous IUPAC nomenclature.
    4. Ignore general English sentences, filler phrases, or reaction notes.
    5. Only return Examples where the number falls between {c_min} and {c_max} (inclusive).
    
    Text content from Page {page_num}:
    \"\"\"
    {page_text}
    \"\"\"
    
    You must output your answer STRICTLY as a JSON list of objects matching this exact structure, with no extra formatting, markdown tags, or explanation:
    [
      {{"Example": 1, "Page Number": {page_num}, "Structure ID": "Example 1", "Corrected IUPAC Name": "actual_cleaned_iupac_name_here"}},
      {{"Example": 2, "Page Number": {page_num}, "Structure ID": "Example 2", "Corrected IUPAC Name": "actual_cleaned_iupac_name_here"}}
    ]
    If no relevant Examples are found, return an empty list: []
    """
    
    try:
        # Request a JSON response from the lightweight and fast Gemini 2.5 Flash model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1 # Low temperature keeps it precise and factual
            ),
        )
        
        # Parse the structured JSON output from the AI
        data = json.loads(response.text)
        return data
    except Exception as e:
        st.warning(f"AI could not parse page {page_num}: {e}")
        return []

# 4. RENDER AND EXECUTION
if uploaded_file is not None:
    if not api_key:
        st.error("🔑 Please enter your Gemini API Key in the sidebar to run the AI extractor.")
    else:
        with st.spinner("Initializing Gemini AI Client and Reading PDF..."):
            try:
                # Setup the official Google GenAI client
                client = genai.Client(api_key=api_key)
                
                file_bytes = uploaded_file.read()
                pdf_data = io.BytesIO(file_bytes)
                reader = PdfReader(pdf_data)
                total_pages = len(reader.pages)
                
                actual_start = max(1, start_page) - 1
                actual_end = min(total_pages, end_page)
                
                st.info(f"🤖 AI is scanning pages {actual_start+1} to {actual_end}...")
                
                all_results = []
                
                # Setup visual tracking blocks
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_to_scan = actual_end - actual_start
                
                # Process page by page using the AI
                for idx, page_idx in enumerate(range(actual_start, actual_end)):
                    page_num = page_idx + 1
                    status_text.text(f"Analyzing page {page_num} with AI...")
                    
                    text_content = reader.pages[page_idx].extract_text()
                    if text_content and text_content.strip():
                        page_data = analyze_page_with_ai(client, text_content, page_num, comp_start, comp_end)
                        if page_data:
                            all_results.extend(page_data)
                    
                    # Update progress bar
                    progress_bar.progress((idx + 1) / total_to_scan)
                
                status_text.text("Extraction complete!")
                
                # Clean up entries (Ensure no duplicate Examples saved across overlapping sections)
                unique_results = []
                seen_examples = set()
                for item in all_results:
                    if item["Example"] not in seen_examples:
                        seen_examples.add(item["Example"])
                        unique_results.append(item)
                        
                # Sort numerically by Example ID
                unique_results.sort(key=lambda x: x["Example"])

                if unique_results:
                    st.success(f"Isolated {len(unique_results)} verified final compounds using AI!")
                    st.dataframe(unique_results, use_container_width=True)
                    
                    # CSV Builder
                    csv_header = "Example,Page Number,Structure ID,Corrected IUPAC Name\n"
                    csv_rows = [f'{r["Example"]},{r["Page Number"]},"{r["Structure ID"]}","{r["Corrected IUPAC Name"]}"' for r in unique_results]
                    csv_data = csv_header + "\n".join(csv_rows)
                    
                    st.download_button(
                        label="Download AI Generated Sheet as CSV",
                        data=csv_data,
                        file_name="ai_iupac_precision_report.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("The AI did not find any matching final compound headings in the specified range.")
                    
            except Exception as e:
                st.error(f"System Error: {e}")
