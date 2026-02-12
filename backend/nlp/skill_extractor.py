import re
from collections import defaultdict

# =========================
# MASTER SKILLS DATABASE
# =========================

SKILLS_DB = {
    "programming": [
        "python", "java", "c++", "javascript", "typescript"
    ],
    "web": [
        "html", "css", "react", "node", "flask", "django"
    ],
    "database": [
        "sql", "mysql", "postgresql", "mongodb"
    ],
    "ai_ml": [
        "machine learning", "deep learning", "nlp", "data science"
    ],
    "tools": [
        "git", "docker", "aws", "linux"
    ]
}

# 🔥 FLATTEN (NO SINGLE LETTER SKILLS)
ALL_SKILLS = set(
    skill for group in SKILLS_DB.values()
    for skill in group
    if len(skill) > 1
)

# =========================
# CLEAN TEXT
# =========================

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# =========================
# CORE EXTRACTION
# =========================

def extract_skills_nlp(text: str):
    text = normalize_text(text)
    skill_counter = defaultdict(int)

    for skill in ALL_SKILLS:
        # 🔒 STRICT WORD BOUNDARY MATCH
        pattern = r"\b" + re.escape(skill) + r"\b"
        matches = re.findall(pattern, text)
        if matches:
            skill_counter[skill] += len(matches)

    # =========================
    # CONFIDENCE CALCULATION
    # =========================

    skills_meta = []
    for skill, freq in skill_counter.items():
        confidence = min(1.0, freq / 3)
        skills_meta.append({
            "skill": skill,
            "confidence": round(confidence, 2)
        })

    # ATS-style sorting
    skills_meta.sort(key=lambda x: x["confidence"], reverse=True)
    return skills_meta

# =========================
# SECTION-AWARE EXTRACTION
# =========================

def extract_skills_from_sections(sections: dict):
    safe_text = []

    for key in ["skills", "experience", "projects"]:
        value = sections.get(key, "")
        if isinstance(value, list):
            safe_text.append(" ".join(map(str, value)))
        elif isinstance(value, str):
            safe_text.append(value)

    combined_text = " ".join(safe_text)
    return extract_skills_nlp(combined_text)
