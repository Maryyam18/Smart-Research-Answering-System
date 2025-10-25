# extract_with_grobid.py
import requests
import os
import time

# GROBID API URL — localhost works for you!
GROBID_URL = "http://localhost:8070/api/processFulltextDocument"

# Your folders
PDF_FOLDER = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers/pdfs"
XML_OUTPUT_FOLDER = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers/extracted"

# Create output folder
os.makedirs(XML_OUTPUT_FOLDER, exist_ok=True)

# Your 6 EMNLP 2024 papers
pdf_files = [
    "2024.emnlp-main.342.pdf",
    "2024.emnlp-main.64.pdf",
    "2024.emnlp-main.992.pdf",
    "2024.emnlp-main.626.pdf",
    "2024.emnlp-main.248.pdf",
    "2024.emnlp-main.15.pdf"
]

def process_pdf(pdf_path):
    filename = os.path.basename(pdf_path)
    print(f"\nProcessing: {filename}")
    
    try:
        with open(pdf_path, "rb") as f:
            files = {"input": (filename, f, "application/pdf")}
            response = requests.post(GROBID_URL, files=files, timeout=120)
        
        if response.status_code == 200:
            xml_filename = os.path.splitext(filename)[0] + ".tei.xml"
            xml_path = os.path.join(XML_OUTPUT_FOLDER, xml_filename)
            with open(xml_path, "w", encoding="utf-8") as out:
                out.write(response.text)
            print(f"SUCCESS: Saved → {xml_filename}")
            return xml_path
        else:
            print(f"ERROR {response.status_code}: {filename}")
            print(response.text[:500])
            return None
    except Exception as e:
        print(f"EXCEPTION: {filename} | {str(e)}")
        return None

# Run all
print("Starting GROBID extraction for 6 papers...\n")
successful = 0
for pdf_file in pdf_files:
    pdf_path = os.path.join(PDF_FOLDER, pdf_file)
    if os.path.exists(pdf_path):
        if process_pdf(pdf_path):
            successful += 1
        time.sleep(2)  # Be gentle on GROBID
    else:
        print(f"NOT FOUND: {pdf_file}")

print(f"\nDONE! {successful}/6 XML files saved in:")
print(XML_OUTPUT_FOLDER)