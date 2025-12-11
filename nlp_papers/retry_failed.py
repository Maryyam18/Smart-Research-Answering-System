# 2_retry_failed.py → Your retry script (with long timeout)
import requests
import os
import time

GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
BASE = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers"

if not os.path.exists("failed_papers.txt"):
    print("No failed papers! You're 100% done")
    exit()

print("RETRYING FAILED PAPERS (6+ minutes timeout)".center(60))
print("-"*60)

with open("failed_papers.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f.readlines() if line.strip()]

success = 0
for line in lines:
    domain, pdf = line.split("|", 1)
    pdf_path = os.path.join(BASE, "pdfs", domain, pdf)
    xml_folder = os.path.join(BASE, "extracted", domain)

    print(f"Retrying → {domain}/{pdf}")

    try:
        with open(pdf_path, "rb") as f:
            files = {"input": (pdf, f, "application/pdf")}
            r = requests.post(GROBID_URL, files=files, timeout=400)

        if r.status_code == 200:
            xml_name = os.path.splitext(pdf)[0] + ".tei.xml"
            xml_path = os.path.join(xml_folder, xml_name)
            with open(xml_path, "w", encoding="utf-8") as out:
                out.write(r.text)
            print("SUCCESS")
            success += 1
        else:
            print(f"Still failed → HTTP {r.status_code}")
    except Exception as e:
        print(f"Exception → {str(e)[:60]}")

    time.sleep(5)

print("-"*60)
print(f"Retry complete! {success}/{len(lines)} recovered")
os.remove("failed_papers.txt")
print("All done! Now run step 2 → 2_parse_xml_to_json.py")