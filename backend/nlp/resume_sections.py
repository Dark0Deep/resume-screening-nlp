import re

def extract_personal_details(text):
    email = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    phone = re.findall(r"\+?\d[\d -]{8,12}\d", text)

    return {
        "name": "",   # later improve
        "email": email[0] if email else "",
        "phone": phone[0] if phone else "",
        "linkedin": "",
        "github": "",
        "portfolio": ""
    }
def extract_education(text):
    education = []

    degree_keywords = [
        "B.Tech", "B.E", "Bachelor", "M.Tech", "M.E",
        "MBA", "MCA", "BCA", "B.Sc", "M.Sc", "PhD"
    ]

    lines = text.split("\n")

    for line in lines:
        for degree in degree_keywords:
            if degree.lower() in line.lower():
                education.append({
                    "degree": degree,
                    "institution": line.strip(),
                    "year": "",
                    "cgpa": ""
                })
                break

    return education
def extract_experience(text):
    experience = []

    keywords = [
        "experience",
        "work experience",
        "professional experience",
        "employment"
    ]

    lines = text.split("\n")
    capture = False

    for line in lines:
        if any(k in line.lower() for k in keywords):
            capture = True
            continue

        if capture:
            if line.strip() == "":
                break

            experience.append({
                "job_title": "",
                "company": line.strip(),
                "duration": "",
                "description": ""
            })

    return experience
def extract_structured_skills(text):
    text = text.lower()

    technical_skills_db = [
        "python", "java", "c++", "sql", "mysql", "mongodb",
        "html", "css", "javascript", "flask", "django",
        "machine learning", "deep learning", "nlp",
        "linux", "git", "docker", "aws"
    ]

    soft_skills_db = [
        "communication", "teamwork", "leadership",
        "problem solving", "critical thinking",
        "time management", "adaptability"
    ]

    certifications_db = [
        "aws", "cisco", "ccna", "azure",
        "google cloud", "oracle"
    ]

    technical = []
    soft = []
    certifications = []

    for skill in technical_skills_db:
        if skill in text:
            technical.append(skill)

    for skill in soft_skills_db:
        if skill in text:
            soft.append(skill)

    for cert in certifications_db:
        if cert in text:
            certifications.append(cert)

    return {
        "technical": list(set(technical)),
        "soft": list(set(soft)),
        "certifications": list(set(certifications))
    }
def extract_projects(text):
    projects = []

    keywords = [
        "projects",
        "project experience",
        "academic projects",
        "personal projects"
    ]

    lines = text.split("\n")
    capture = False

    for line in lines:
        if any(k in line.lower() for k in keywords):
            capture = True
            continue

        if capture:
            if line.strip() == "":
                break

            projects.append({
                "title": line.strip(),
                "tools": [],
                "description": ""
            })

    return projects

def extract_achievements(text):
    achievements = []
    keywords = ["achievement", "achievements", "awards", "honors"]

    lines = text.split("\n")
    capture = False

    for line in lines:
        if any(k in line.lower() for k in keywords):
            capture = True
            continue

        if capture:
            if line.strip() == "":
                break
            achievements.append(line.strip())

    return achievements


def extract_languages(text):
    programming_languages = []
    spoken_languages = []

    prog_langs = ["python", "java", "c++", "javascript", "sql"]
    human_langs = ["english", "hindi", "french", "german", "spanish"]

    lower_text = text.lower()

    for lang in prog_langs:
        if lang in lower_text:
            programming_languages.append(lang)

    for lang in human_langs:
        if lang in lower_text:
            spoken_languages.append(lang)

    return {
        "programming": list(set(programming_languages)),
        "spoken": list(set(spoken_languages))
    }


def extract_extra_sections(text):
    extras = []
    keywords = [
        "internship",
        "internships",
        "volunteer",
        "volunteering",
        "publication",
        "research",
        "extracurricular"
    ]

    lines = text.split("\n")

    for line in lines:
        if any(k in line.lower() for k in keywords):
            extras.append(line.strip())

    return extras
