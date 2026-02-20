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

def calculate_simple_ats(resume):
    """
    Improved professional ATS scoring (0–100)
    Produces natural percentage-based scores
    """

    score = 0

    # =========================
    # 1️⃣ SKILLS (40%)
    # =========================
    skills = resume.get("skills", [])
    unique_skills = len(set(skills))

    # Normalize skill score (assuming 12 skills = strong profile)
    skill_score = min((unique_skills / 12) * 40, 40)


    # =========================
    # 2️⃣ EXPERIENCE (25%)
    # =========================
    experience = resume.get("experience", [])
    years_weight = len(experience)

    exp_score = min((years_weight / 5) * 25, 25)


    # =========================
    # 3️⃣ EDUCATION QUALITY (15%)
    # =========================
    education = str(resume.get("education", "")).lower()

    edu_score = 0
    if "phd" in education:
        edu_score = 15
    elif "master" in education or "m.tech" in education or "mba" in education:
        edu_score = 12
    elif "bachelor" in education or "b.tech" in education:
        edu_score = 10
    elif education:
        edu_score = 6


    # =========================
    # 4️⃣ CONTENT STRENGTH (20%)
    # =========================
    raw_text = resume.get("raw_text", "")
    length = len(raw_text)

    content_score = min((length / 2000) * 20, 20)


    # =========================
    # FINAL SCORE
    # =========================
    final_score = skill_score + exp_score + edu_score + content_score

    return round(min(final_score, 100), 2)

