# retry_failed.py
import requests
import os

GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
PDF_FOLDER = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers/pdfs"
XML_OUTPUT_FOLDER = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers/extracted"

# Only the failed one
pdf_file = "1009.1796v1.pdf"
pdf_path = os.path.join(PDF_FOLDER, pdf_file)

print(f"Retrying: {pdf_file} with 300s timeout...")

try:
    with open(pdf_path, "rb") as f:
        files = {"input": (pdf_file, f, "application/pdf")}
        response = requests.post(GROBID_URL, files=files, timeout=300)  # 5 minutes!

    if response.status_code == 200:
        xml_filename = "1009.1796v1.tei.xml"
        xml_path = os.path.join(XML_OUTPUT_FOLDER, xml_filename)
        with open(xml_path, "w", encoding="utf-8") as out:
            out.write(response.text)
        print(f"SUCCESS: Saved → {xml_filename}")
    else:
        print(f"Still failed: {response.status_code}")
        print(response.text[:500])
except Exception as e:
    print(f"EXCEPTION: {str(e)}")