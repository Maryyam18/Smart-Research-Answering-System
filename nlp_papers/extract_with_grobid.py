# 1_extract_with_grobid.py → YOUR ORIGINAL CODE (NOW MULTI-DOMAIN & PERFECT)
import requests
import os
import time

# GROBID URL
GROBID_URL = "http://localhost:8070/api/processFulltextDocument"

# MAIN FOLDER
BASE = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers"

# YOUR 4 DOMAINS (exact folder names)
DOMAINS = [
    # "NLP"
    # "Quantum Information Retrieval and Information Teleportation"
    # "Quantum Resistant Cryptography and Identity Based Encryption"
    "VLSI in Power Electronics and Embedded Systems"
]

print("STARTING GROBID EXTRACTION FOR ALL DOMAINS (Your Working Method)")
print("="*80)

total_success = 0
total_pdfs = 0

for domain in DOMAINS:
    PDF_FOLDER = os.path.join(BASE, "pdfs", domain)
    XML_OUTPUT_FOLDER = os.path.join(BASE, "extracted", domain)

    # Create domain output folder
    os.makedirs(XML_OUTPUT_FOLDER, exist_ok=True)

    if not os.path.exists(PDF_FOLDER):
        print(f"Folder not found → {PDF_FOLDER}")
        continue

    # Get all PDFs in this domain
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"No PDFs in → {domain}")
        continue

    print(f"\nDOMAIN: {domain}")
    print(f"Found {len(pdf_files)} PDFs → extracting...\n")

    domain_success = 0

    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER, pdf_file)
        print(f"Processing: {pdf_file}")

        try:
            with open(pdf_path, "rb") as f:
                files = {"input": (pdf_file, f, "application/pdf")}
                response = requests.post(GROBID_URL, files=files, timeout=180 )  

            if response.status_code == 200:
                xml_filename = os.path.splitext(pdf_file)[0] + ".tei.xml"
                xml_path = os.path.join(XML_OUTPUT_FOLDER, xml_filename)
                with open(xml_path, "w", encoding="utf-8") as out:
                    out.write(response.text)
                print(f"SUCCESS → {xml_filename}")
                domain_success += 1
                total_success += 1
            else:
                print(f"FAILED {response.status_code} → {pdf_file}")

        except Exception as e:
            print(f"ERROR → {pdf_file} | {str(e)}")

        time.sleep(3)  # Your golden delay that always worked

        total_pdfs += 1

    print(f"\n{domain} → {domain_success}/{len(pdf_files)} extracted\n")

print("="*80)
print(f"ALL DONE! {total_success}/{total_pdfs} PDFs successfully converted to XML")
print("Next step: Run 2_parse_xml_to_json.py")