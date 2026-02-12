def generate_ats_feedback(resume_text, resume_data, ats_result):

    suggestions = []

    ats_score = ats_result.get("ats_score", 0)

    skills = resume_data.get("skills", [])
    experience = resume_data.get("experience", [])
    projects = resume_data.get("projects", [])
    education = resume_data.get("education", "")
    raw_text = resume_text.lower()

    # ================= ATS SCORE =================
    if ats_score < 40:
        suggestions.append(
            "Your ATS score is very low. Improve keyword matching and add relevant technical skills."
        )
    elif ats_score < 60:
        suggestions.append(
            "Your ATS score is moderate. Add more role-specific keywords and measurable achievements."
        )

    # ================= SKILLS =================
    if not skills:
        suggestions.append(
            "No technical skills detected. Add a dedicated 'Skills' section with tools and technologies."
        )
    elif len(skills) < 5:
        suggestions.append(
            "Add more relevant technical skills to strengthen your profile."
        )

    # ================= PROJECTS =================
    if not projects:
        suggestions.append(
            "Projects section is missing. Add 2–3 practical projects with clear descriptions and impact."
        )

    # ================= EXPERIENCE =================
    if not experience:
        suggestions.append(
            "No work experience detected. Consider adding internships or practical experience."
        )

    # ================= EDUCATION =================
    if not education:
        suggestions.append(
            "Education details are missing. Add degree, university name and year."
        )

    # ================= RESUME LENGTH =================
    if len(raw_text.split()) < 250:
        suggestions.append(
            "Resume is too short. Add more details about projects, skills and responsibilities."
        )

    # ================= ACTION VERBS =================
    action_words = ["developed", "designed", "implemented", "built", "optimized"]
    if not any(word in raw_text for word in action_words):
        suggestions.append(
            "Use strong action verbs like 'Developed', 'Designed', 'Implemented' to improve impact."
        )

    # ================= DEFAULT =================
    if not suggestions:
        suggestions.append(
            "Your resume looks strong. Consider tailoring it according to specific job descriptions."
        )

    return suggestions
