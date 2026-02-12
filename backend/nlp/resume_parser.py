import re
import spacy
import PyPDF2
import docx
import phonenumbers
from collections import defaultdict

nlp = spacy.load("en_core_web_sm")

# ======================================================
# TEXT EXTRACTION
# ======================================================

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text


def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_resume_text(file_path):
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    if file_path.endswith(".docx"):
        return extract_text_from_docx(file_path)
    if file_path.endswith(".txt"):
        return extract_text_from_txt(file_path)
    return ""

# ======================================================
# BASIC INFO (STRICT & SAFE)
# ======================================================

def extract_email(text):
    m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return m.group() if m else None


def extract_phone(text):
    for match in phonenumbers.PhoneNumberMatcher(text, "IN"):
        return phonenumbers.format_number(
            match.number, phonenumbers.PhoneNumberFormat.E164
        )
    return None


def extract_name(text, email):
    """
    Name rules:
    - Appears in first 10 lines
    - Not email / phone / skill / keyword
    - Max 4 words
    """
    lines = [l.strip() for l in text.split("\n")[:10] if l.strip()]
    blacklist = re.compile(
        r"(email|phone|contact|skills|experience|education|project)",
        re.I
    )

    for line in lines:
        if email and email in line:
            continue
        if blacklist.search(line):
            continue
        if 1 <= len(line.split()) <= 4 and not re.search(r"\d", line):
            return line

    return None


def extract_location(text):
    """
    Only REAL locations
    """
    doc = nlp(text[:1200])
    locations = []
    blacklist = {
        "python", "flask", "django", "sql", "ai", "ml",
        "html", "css", "javascript", "react"
    }

    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC"):
            val = ent.text.lower()
            if val not in blacklist and len(val) > 2:
                locations.append(ent.text)

    return list(dict.fromkeys(locations))[:2]

# ======================================================
# SECTION SPLITTING (STABLE)
# ======================================================

SECTION_HEADERS = {
    "skills": ["skills", "technical skills"],
    "education": ["education", "academics"],
    "experience": ["experience", "work experience", "employment"],
    "projects": ["projects"],
    "certifications": ["certifications", "certificates"],
    "publications": ["publications", "research"],
    "hobbies": ["hobbies", "interests"]
}

def split_sections(text):
    sections = defaultdict(list)
    current = None

    for line in text.split("\n"):
        clean = line.strip().lower()

        matched = False
        for key, headers in SECTION_HEADERS.items():
            if any(clean == h or clean.startswith(h) for h in headers):
                current = key
                matched = True
                break

        if not matched and current:
            sections[current].append(line.strip())

    return {
        k: "\n".join(v).strip()
        for k, v in sections.items()
        if v
    }

# ======================================================
# EXPERIENCE PARSING (NO METHODS BUG)
# ======================================================

def parse_experience(text):
    if not text:
        return []

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    experience = []

    for line in lines:
        experience.append({
            "title": line,
            "company": "",
            "duration": "",
            "description": ""
        })

    return experience

# ======================================================
# FINAL PARSER
# ======================================================

def parse_resume(file_path):
    raw_text = extract_resume_text(file_path)
    clean_text = re.sub(r"\s+", " ", raw_text)

    sections = split_sections(raw_text)

    email = extract_email(clean_text)

    parsed = {
        "name": extract_name(raw_text, email),
        "email": email,
        "phone": extract_phone(clean_text),
        "location": extract_location(raw_text),

        "skills": sections.get("skills", ""),
        "education": sections.get("education", ""),
        "experience": parse_experience(sections.get("experience", "")),
        "projects": sections.get("projects", "").split("\n") if sections.get("projects") else [],
        "certifications": sections.get("certifications", ""),
        "publications": sections.get("publications", ""),
        "hobbies": sections.get("hobbies", ""),

        "raw_text": raw_text
    }

    return parsed
