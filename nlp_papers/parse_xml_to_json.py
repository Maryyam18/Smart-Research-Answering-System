# 2_parse_xml_to_json.py
import os, json, re
from lxml import etree

BASE = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers"
DOMAINS = ["NLP", "Quantum Information Retrieval and Information Teleportation", "Quantum Resistant Cryptography and Identity Based Encryption", "VLSI in Power Electronics and Embedded Systems"]


NS = {"tei": "http://www.tei-c.org/ns/1.0"}

def clean(t): return "" if t is None else etree.tostring(t, method="text", encoding="unicode").strip()

def get_year(root):
    date = root.find(".//tei:teiHeader//tei:date", NS)
    if date is not None:
        if date.get("when"): return int(date.get("when")[:4])
        if date.text and (m := re.search(r"\b(19|20)\d{2}\b", date.text)): return int(m.group())
    return 2024

for domain in DOMAINS:
    xml_dir = os.path.join(BASE, "extracted", domain)
    json_dir = os.path.join(BASE, "json_clean", domain)
    os.makedirs(json_dir, exist_ok=True)

    if not os.path.exists(xml_dir):
        print(f"Skipping {domain} (no extracted folder)")
        continue

    files = [f for f in os.listdir(xml_dir) if f.endswith(".tei.xml")]
    print(f"Parsing {domain} → {len(files)} files")

    for f in files:
        path = os.path.join(xml_dir, f)
        tree = etree.parse(path)
        root = tree.getroot()

        paperid = os.path.splitext(f)[0].replace(".tei", "")

        data = {
            "paperid": paperid,
            "title": clean(root.find(".//tei:titleStmt/tei:title", NS)) or "Unknown Title",
            "authors": [a.text.strip() for a in root.findall(".//tei:author//tei:surname", NS) if a.text and a.text.strip()] or ["Unknown"],
            "year": get_year(root),
            "abstract": clean(root.find(".//tei:abstract", NS)),
            "sections": []
        }

        for div in root.findall(".//tei:body//tei:div", NS):
            head = div.find("tei:head", NS)
            heading = clean(head) if head is not None else ""
            if any(x in heading.lower() for x in ["appendix", "reference", "bibliography", "acknowledgment", "acknowledgement"]):
                continue
            text = " ".join(clean(p) for p in div.findall(".//tei:p", NS))
            if len(text) > 100:
                data["sections"].append({"heading": heading, "text": text[:9000]})

        json_path = os.path.join(json_dir, paperid + ".json")
        with open(json_path, "w", encoding="utf-8") as j:
            json.dump(data, j, indent=2, ensure_ascii=False)
        print(f"   Saved → {data['title'][:70]} ({data['year']})")

    print(f"{domain} → JSON conversion complete!\n")