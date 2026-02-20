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
# BASIC INFO
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
    lines = [l.strip() for l in text.split("\n")[:10] if l.strip()]
    blacklist = re.compile(r"(email|phone|contact|skills|experience|education|project)", re.I)

    for line in lines:
        if email and email in line:
            continue
        if blacklist.search(line):
            continue
        if 1 <= len(line.split()) <= 4 and not re.search(r"\d", line):
            return line
    return None


def extract_location(text):
    doc = nlp(text[:1200])
    locations = []

    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC"):
            locations.append(ent.text)

    return list(dict.fromkeys(locations))[:2]


# ======================================================
# SECTION SPLITTING (IMPROVED)
# ======================================================

SECTION_HEADERS = {
    "skills": ["skills", "technical skills", "core skills"],
    "education": ["education", "academics", "academic background"],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history"
    ],
    "projects": [
        "projects",
        "academic projects",
        "key projects",
        "relevant projects",
        "project experience"
    ],
    "certifications": ["certifications", "certificates"],
    "publications": ["publications", "research"],
    "hobbies": ["hobbies", "interests"]
}


def split_sections(text):
    sections = defaultdict(list)
    current = None

    for line in text.split("\n"):
        clean = line.strip()
        lower = clean.lower()
        normalized = re.sub(r"[^a-z\s]", "", lower)

        matched = None
        for key, headers in SECTION_HEADERS.items():
            if any(h in normalized for h in headers):
                matched = key
                break

        if matched:
            current = matched
            continue

        if current and clean:
            sections[current].append(clean)

    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


# ======================================================
# STRUCTURED EXPERIENCE PARSER
# ======================================================

def parse_experience(text):
    if not text:
        return []

    blocks = re.split(r"\n\s*\n", text)
    structured = []

    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue

        title = lines[0]

        duration_match = re.search(
            r"(19|20)\d{2}.*?(present|current|(19|20)\d{2})?",
            block,
            re.I
        )
        duration = duration_match.group(0) if duration_match else ""

        points = []
        for line in lines[1:]:
            clean = line.lstrip("•- ")
            if len(clean) > 3:
                points.append(clean)

        structured.append({
            "title": title,
            "company": "",
            "duration": duration,
            "points": points
        })

    return structured


# ======================================================
# STRUCTURED PROJECT PARSER
# ======================================================

def parse_projects(text):
    if not text:
        return []

    blocks = re.split(r"\n\s*\n", text)
    structured = []

    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue

        name = lines[0]
        tech_stack = []
        points = []

        for line in lines[1:]:
            clean = line.lstrip("•- ")

            if "tech stack" in clean.lower():
                tech_stack = [t.strip() for t in clean.split(":")[-1].split(",")]
            elif len(clean) > 3:
                points.append(clean)

        structured.append({
            "name": name,
            "tech_stack": tech_stack,
            "points": points
        })

    return structured


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

        "skills": [s.strip() for s in sections.get("skills", "").split("\n") if s.strip()],
        "education": sections.get("education", ""),
        "experience": parse_experience(sections.get("experience", "")),
        "projects": parse_projects(sections.get("projects", "")),
        "certifications": sections.get("certifications", ""),
        "publications": sections.get("publications", ""),
        "hobbies": sections.get("hobbies", ""),

        "raw_text": raw_text
    }

    return parsed