def generate_ats_feedback(resume_data):
    score = 0
    feedback = []
    suggestions = []

    skills = resume_data.get("skills", {})
    experience = resume_data.get("experience", [])
    projects = resume_data.get("projects", [])
    education = resume_data.get("education", [])

    # ===== SKILLS =====
    skills = resume_data.get("skills", [])

# skills agar list ho
    if isinstance(skills, list) and len(skills) > 0:
        score += 40
        feedback.append("Your resume includes relevant technical skills.")
    else:
        suggestions.append("Add more technical skills aligned with your target role.")


    # ===== EXPERIENCE =====
    if experience:
        score += 25
        feedback.append("Work experience section is present.")
    else:
        suggestions.append("Include internships or work experience to strengthen your profile.")

    # ===== PROJECTS =====
    if projects:
        score += 20
        feedback.append("Projects section adds practical credibility.")
    else:
        suggestions.append("Add academic or professional projects with tools used.")

    # ===== EDUCATION =====
    if education:
        score += 15
        feedback.append("Education details are clearly mentioned.")
    else:
        suggestions.append("Mention your educational background clearly.")

    # ===== FINAL FEEDBACK =====
    if score >= 75:
        overall = "Your resume is ATS-friendly and well-structured. You are a strong candidate."
    elif score >= 50:
        overall = "Your resume is moderately ATS-optimized but can be improved further."
    else:
        overall = "Your resume needs improvement to perform well in ATS screening."

    return {
        "ats_score": score,
        "overall_feedback": overall,
        "strengths": feedback,
        "suggestions": suggestions
    }
