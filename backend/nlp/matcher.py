import math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# -------------------------
# 1️⃣ SEMANTIC SIMILARITY
# -------------------------

def semantic_similarity(resume_text, job_description):
    documents = [resume_text, job_description]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_df=0.85
    )

    tfidf = vectorizer.fit_transform(documents)
    similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]

    return round(similarity * 100, 2)


# -------------------------
# 2️⃣ SKILL MATCH SCORE
# -------------------------

def skill_match_score(resume_skills, required_skills):
    """
    resume_skills = [
        {"skill": "python", "confidence": 1.0},
        {"skill": "flask", "confidence": 0.7}
    ]
    required_skills = ["python", "flask", "sql"]
    """

    if not required_skills:
        return 0

    matched = 0
    weighted_score = 0

    for req in required_skills:
        for rs in resume_skills:
            if req.lower() == rs["skill"]:
                matched += 1
                weighted_score += rs["confidence"]

    raw_score = weighted_score / len(required_skills)
    return round(min(raw_score * 100, 100), 2)


# -------------------------
# 3️⃣ SECTION QUALITY SCORE
# -------------------------

def section_quality_score(sections):
    """
    sections = {
        "experience": "...",
        "projects": "...",
        "certifications": "..."
    }
    """

    score = 0

    if len(sections.get("experience", "")) > 200:
        score += 40
    elif len(sections.get("experience", "")) > 80:
        score += 25

    if len(sections.get("projects", "")) > 100:
        score += 35
    elif len(sections.get("projects", "")) > 40:
        score += 20

    if sections.get("certifications"):
        score += 25

    return min(score, 100)


# -------------------------
# 🔥 FINAL ATS MATCH SCORE
# -------------------------

def calculate_ats_score(resume_text, job_description, resume_skills, sections, required_skills):
    """
    FINAL ATS SCORE (0–100)

    Weight distribution:
    - Skill match: 50%
    - Semantic similarity: 30%
    - Section quality: 20%
    """

    skill_score = skill_match_score(resume_skills, required_skills)
    semantic_score = semantic_similarity(resume_text, job_description)
    section_score = section_quality_score(sections)

    final_score = (
        (0.5 * skill_score) +
        (0.3 * semantic_score) +
        (0.2 * section_score)
    )

    return {
        "ats_score": round(final_score, 2),
        "skill_score": skill_score,
        "semantic_score": semantic_score,
        "section_score": section_score
    }
def calculate_simple_ats(resume, job_criteria):
    score = 0

    # -------- SKILLS (50) --------
    required_skills = job_criteria.get("skills", [])
    resume_skills = [s.lower() for s in resume.get("skills", [])]

    if required_skills:
        matched = sum(1 for s in required_skills if s in resume_skills)
        score += (matched / len(required_skills)) * 50

    # -------- EDUCATION (20) --------
    degree = job_criteria.get("degree", "").lower()
    education_text = str(resume.get("education", "")).lower()

    if degree and degree in education_text:
        score += 20

    # -------- EXPERIENCE (20) --------
    experience = resume.get("experience", [])
    if isinstance(experience, list) and len(experience) > 0:
        score += min(len(experience) * 5, 20)

    # -------- JD KEYWORDS (10) --------
    jd = job_criteria.get("job_description", "").lower()
    raw_text = resume.get("raw_text", "").lower()

    if jd:
        keywords = jd.split()
        match_count = sum(1 for k in keywords if k in raw_text)
        score += min((match_count / len(keywords)) * 10, 10)

    return round(score, 2)

def calculate_simple_ats(resume):
    """
    Simple professional ATS score without JD
    Based on resume completeness & keyword strength
    """

    score = 0

    # ===== Skills =====
    skills = resume.get("skills", [])
    if skills:
        score += min(len(skills) * 5, 30)   # max 30

    # ===== Experience =====
    experience = resume.get("experience", [])
    if experience:
        score += min(len(experience) * 10, 30)  # max 30

    # ===== Education =====
    education = resume.get("education", "")
    if education:
        score += 15

    # ===== Resume Length / Content =====
    raw_text = resume.get("raw_text", "")
    if raw_text:
        if len(raw_text) > 1500:
            score += 15
        elif len(raw_text) > 800:
            score += 10
        else:
            score += 5

    # Safety cap
    return min(score, 100)


