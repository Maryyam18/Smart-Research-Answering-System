# parse_xml_to_json.py — FIXED VERSION
import os
import json
from lxml import etree
from pathlib import Path

XML_FOLDER = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers/extracted"
JSON_OUTPUT_FOLDER = "E:/5th_Semester/SPM/Smart_Research_Answering_System/nlp_papers/json_clean"

os.makedirs(JSON_OUTPUT_FOLDER, exist_ok=True)
NS = {"tei": "http://www.tei-c.org/ns/1.0"}

def is_likely_author_name(name):
    if not name or len(name.strip()) < 3:
        return False
    name = name.lower()
    bad = ["et al", "doi:", "arxiv", "http", "2024", "2025", "appendix", "table", "figure", "eq", "eq.", "fig"]
    if any(x in name for x in bad):
        return False
    if name.count(" ") == 0 and not name[0].isupper():
        return False
    return True

def extract_authors(root):
    authors = []
    author_elems = root.findall(".//tei:titleStmt/tei:author", NS)
    if not author_elems:
        author_elems = root.findall(".//tei:author", NS)[:10]  # Fallback, limit to 10
    for auth in author_elems:
        forename = auth.find("tei:persName/tei:forename", NS)
        surname = auth.find("tei:persName/tei:surname", NS)
        full = ""
        if forename is not None and surname is not None:
            full = f"{forename.text or ''} {surname.text or ''}".strip()
        elif auth.find("tei:persName", NS) is not None:
            full = " ".join([t.text or "" for t in auth.find("tei:persName", NS) if t.text]).strip()
        if full and is_likely_author_name(full):
            authors.append(full)
        if len(authors) >= 20:  # Max 20 authors
            break
    return authors if authors else ["Unknown"]

def extract_abstract(root):
    abstract = root.find(".//tei:abstract/tei:p", NS)
    if abstract is None:
        abstract = root.find(".//tei:abstract", NS)
    if abstract is not None:
        return etree.tostring(abstract, method="text", encoding="unicode").strip()
    return ""

def extract_sections(root):
    sections = []
    body = root.find(".//tei:body", NS)
    if not body:
        return sections
    for div in body.findall("tei:div", NS):
        head = div.find("tei:head", NS)
        heading = head.text.strip() if head is not None and head.text else "Untitled"
        # Skip appendices and junk
        if any(x in heading.lower() for x in ["appendix", "reference", "bibliography", "acknowledgment"]):
            continue
        paragraphs = []
        for p in div.findall(".//tei:p", NS):
            text = etree.tostring(p, method="text", encoding="unicode").strip()
            if text and len(text) > 20:
                paragraphs.append(text)
        if paragraphs:
            sections.append({
                "heading": heading,
                "text": " ".join(paragraphs)[:5000]  # Limit per section
            })
    return sections

def extract_figures(root):
    figures = []
    for fig in root.findall(".//tei:figure", NS):
        if fig.get("type") == "table":
            continue
        caption_elem = fig.find("tei:figDesc", NS) or fig.find("tei:head", NS)
        caption = caption_elem.text.strip() if caption_elem is not None and caption_elem.text else "No caption"
        if "table" in caption.lower():
            continue
        graphic = fig.find("tei:graphic", NS)
        img_path = graphic.get("url") if graphic is not None else None
        if caption and len(caption) > 10:
            figures.append({"caption": caption, "image_path": img_path})
    return figures[:20]

def extract_equations(root):
    equations = []
    for formula in root.findall(".//tei:formula[@type='inline']", NS):
        continue
    for formula in root.findall(".//tei:formula", NS):
        math = formula.find("tei:math", NS)
        if math is not None and math.text:
            tex = math.text.strip()
            if len(tex) > 5:
                equations.append(tex)
    return equations[:50]

# === MAIN LOOP ===
xml_files = [f for f in os.listdir(XML_FOLDER) if f.endswith(".tei.xml")]

for xml_file in xml_files:
    xml_path = os.path.join(XML_FOLDER, xml_file)
    print(f"Parsing: {xml_file}")
    tree = etree.parse(xml_path)
    root = tree.getroot()

    data = {
        "paperid": Path(xml_file).stem.replace(".tei", ""),
        "title": (root.find(".//tei:titleStmt/tei:title", NS).text or "").strip(),
        "authors": extract_authors(root),
        "year": 2024,
        "abstract": extract_abstract(root),
        "sections": extract_sections(root),
        "figures": extract_figures(root),
        "equations": extract_equations(root)
    }

    json_path = os.path.join(JSON_OUTPUT_FOLDER, xml_file.replace(".tei.xml", ".json"))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"SAVED: {os.path.basename(json_path)}")

print(f"\nDONE! {len(xml_files)} CLEAN JSON files → {JSON_OUTPUT_FOLDER}")