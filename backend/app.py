from flask import Flask, render_template, request, redirect, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import os

# ================= NLP =================
from nlp.resume_parser import parse_resume
from nlp.skill_extractor import extract_skills_from_sections
from nlp.matcher import calculate_ats_score
from nlp.feedback_engine import generate_ats_feedback
from nlp.matcher import calculate_simple_ats
from nlp.matcher import calculate_ats_score

# ================= DB =================
from db import users_collection, resumes_collection

# ================= APP =================
app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "backend/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ======================================================
# AUTH
# ======================================================

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        user = users_collection.find_one({"email": email, "role": role})
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = str(user["_id"])
            session["role"] = role
            session["name"] = user.get("name", "User")
            return redirect("/recruiter-dashboard" if role == "Recruiter" else "/candidate/dashboard")

        flash("❌ Invalid credentials")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        users_collection.insert_one({
            "name": request.form["name"],
            "email": request.form["email"],
            "password": generate_password_hash(request.form["password"]),
            "role": request.form["role"]
        })
        flash("✅ Registration successful")
        return redirect("/login")
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ======================================================
# CANDIDATE
# ======================================================

@app.route("/candidate/dashboard")
def candidate_dashboard():
    resumes = list(
        resumes_collection.find({"uploaded_by": session.get("user_id")})
        .sort("uploaded_at", -1)
    )
    return render_template("candidate/dashboard.html", resumes=resumes)


@app.route("/candidate/upload")
def candidate_upload():
    return render_template("candidate/upload.html")


@app.route("/candidate/suggestions")
def candidate_suggestions():
    resume = resumes_collection.find_one(
        {"uploaded_by": session.get("user_id"), "status": "analyzed"},
        sort=[("uploaded_at", -1)]
    )
    return render_template("candidate/suggestions.html", resume=resume)


# ======================================================
# UPLOAD
# ======================================================

@app.route("/upload-resume", methods=["POST"])
def upload_resume():
    file = request.files.get("resume")
    if not file or file.filename == "":
        flash("❌ No file selected")
        return redirect("/candidate/upload")

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    user_id = session.get("user_id")

    resumes_collection.update_many(
        {"uploaded_by": user_id},
        {"$set": {"is_active": False}}
    )

    resumes_collection.insert_one({
        "uploaded_by": user_id,
        "filename": file.filename,
        "file_path": file_path,
        "uploaded_at": datetime.utcnow(),
        "is_active": True,
        "status": "uploaded"
    })

    flash("✅ Resume uploaded")
    return redirect("/candidate/dashboard")

# ======================================================
# DELETE RESUME
# ======================================================

@app.route("/candidate/delete-resume/<resume_id>", methods=["POST"])
def delete_resume(resume_id):
    user_id = session.get("user_id")

    resume = resumes_collection.find_one({
        "_id": ObjectId(resume_id),
        "uploaded_by": user_id
    })

    if not resume:
        flash("Resume not found")
        return redirect("/candidate/dashboard")

    try:
        if os.path.exists(resume["file_path"]):
            os.remove(resume["file_path"])
    except:
        pass

    resumes_collection.delete_one({"_id": resume["_id"]})
    flash("🗑️ Resume deleted successfully")
    return redirect("/candidate/dashboard")

# ======================================================
# ANALYZE RESUME
# ======================================================

@app.route("/analyze-resume", methods=["POST"])
def analyze_resume():
    user_id = session.get("user_id")

    resume = resumes_collection.find_one({
        "uploaded_by": user_id,
        "is_active": True
    })

    if not resume:
        flash("❌ Upload a resume first")
        return redirect("/candidate/dashboard")

    parsed = parse_resume(resume["file_path"])

    personal_details = {
        "name": parsed.get("name"),
        "email": parsed.get("email"),
        "phone": parsed.get("phone"),
        "location": ", ".join(parsed.get("location", []))
    }

    projects = parsed.get("projects", [])
    if isinstance(projects, str):
        projects = [projects]

    sections = {
        "skills": parsed.get("skills", ""),
        "experience": " ".join([e.get("title", "") for e in parsed.get("experience", [])]),
        "projects": " ".join(projects)
    }

    skills_meta = extract_skills_from_sections(sections)
    skills = [s["skill"] for s in skills_meta]

    raw_text = parsed.get("raw_text", "")
    summary = raw_text[:400] + "..." if raw_text else "No summary available."

    ats_score = calculate_simple_ats({
    "skills": skills,
    "experience": parsed.get("experience", []),
    "education": parsed.get("education", ""),
    "raw_text": raw_text
})

    ats_feedback = generate_ats_feedback(
        resume_text=raw_text,
        resume_data={
            "personal_details": personal_details,
            "skills": skills,
            "experience": parsed.get("experience", []),
            "projects": projects,
            "education": parsed.get("education", "")
        },
        ats_result={"ats_score": ats_score}
    )

    resumes_collection.update_one(
        {"_id": resume["_id"]},
        {"$set": {
            "personal_details": personal_details,
            "summary": summary,
            "skills": skills,
            "skills_meta": skills_meta,
            "experience": parsed.get("experience", []),
            "projects": projects,
            "education": parsed.get("education", ""),
            "raw_text": raw_text,
            "ats_score": ats_score,
            "ats_feedback": ats_feedback,
            "status": "analyzed"
        }}
    )   

    flash("✅ Resume analyzed successfully")
    return redirect(f"/candidate/analysis/{resume['_id']}")

# ======================================================
# VIEW ANALYSIS
# ======================================================

@app.route("/candidate/analysis/<resume_id>")
def candidate_analysis(resume_id):
    resume = resumes_collection.find_one({"_id": ObjectId(resume_id)})
    return render_template("candidate/analysis.html", resume=resume)


@app.route("/candidate/analysis/latest")
def latest_analysis():
    resume = resumes_collection.find_one(
        {"uploaded_by": session.get("user_id"), "status": "analyzed"},
        sort=[("uploaded_at", -1)]
    )
    if not resume:
        flash("No analyzed resume found")
        return redirect("/candidate/dashboard")

    return redirect(f"/candidate/analysis/{resume['_id']}")

# ======================================================
# RECRUITER SIDE (FINAL & STABLE)
# ======================================================

@app.route("/recruiter-dashboard")
def recruiter_dashboard():
    if session.get("role") != "Recruiter":
        return redirect("/login")

    total = resumes_collection.count_documents({})
    analyzed = resumes_collection.count_documents({"status": "analyzed"})
    shortlisted = resumes_collection.count_documents({"status": "shortlisted"})
    rejected = resumes_collection.count_documents({"status": "rejected"})

    return render_template(
        "recruiter_dashboard.html",
        total=total,
        analyzed=analyzed,
        shortlisted=shortlisted,
        rejected=rejected
    )


@app.route("/recruiter/candidates")
def recruiter_candidates():
    if session.get("role") != "Recruiter":
        return redirect("/login")

    status = request.args.get("status", "all")
    page = int(request.args.get("page", 1))
    limit = 5
    skip = (page - 1) * limit

    query = {}
    if status != "all":
        query["status"] = status

    total = resumes_collection.count_documents(query)

    pipeline = [
        {"$match": query},
        {"$addFields": {"user_obj": {"$toObjectId": "$uploaded_by"}}},
        {"$lookup": {
            "from": "users",
            "localField": "user_obj",
            "foreignField": "_id",
            "as": "candidate"
        }},
        {"$unwind": "$candidate"},
        {"$skip": skip},
        {"$limit": limit}
    ]

    candidates = list(resumes_collection.aggregate(pipeline))
    pages = (total + limit - 1) // limit

    return render_template(
        "recruiter/recruiter_candidates.html",
        candidates=candidates,
        page=page,
        pages=pages,
        status=status
    )

@app.route("/analyze-job", methods=["POST"])
def analyze_job():
    if session.get("role") != "Recruiter":
        return redirect("/login")

    job_description = request.form.get("job_description")

    ranked = []

    for r in resumes_collection.find({"status": "analyzed"}):
        ats = calculate_ats_score(
            resume_text=r.get("raw_text", ""),
            job_description=job_description,
            resume_skills=r.get("skills_meta", []),
            sections={
                "experience": r.get("experience", ""),
                "projects": r.get("projects", ""),
                "certifications": r.get("certifications", "")
            },
            required_skills=[]
        )

        resumes_collection.update_one(
            {"_id": r["_id"]},
            {"$set": ats}
        )

        ranked.append({
            "id": str(r["_id"]),
            "filename": r["filename"],
            "ats_score": ats["ats_score"],
            "status": r.get("status", "analyzed")
        })

    ranked.sort(key=lambda x: x["ats_score"], reverse=True)
    session["ranked_candidates"] = ranked

    flash("✅ Candidates ranked successfully")
    return redirect("/recruiter-dashboard")

@app.route("/recruiter/filter-candidates", methods=["POST"])
def recruiter_filter_candidates():
    if session.get("role") != "Recruiter":
        return redirect("/login")

    degree = request.form.get("degree", "").lower()
    skills = [s.strip().lower() for s in request.form.get("skills", "").split(",") if s.strip()]
    min_ats = int(request.form.get("min_ats", 0))
    job_description = request.form.get("job_description", "")

    shortlisted_count = 0

    resumes = resumes_collection.find({"status": "analyzed"})

    for r in resumes:

    # ---------- DEGREE MATCH (SMART) ----------
        edu_text = str(r.get("education", "")).lower()

        degree_keywords = {
        "b.tech": ["b.tech", "bachelor of technology", "bachelor"],
        "m.tech": ["m.tech", "master of technology", "master"],
        "mba": ["mba", "master of business"],
        "mca": ["mca", "master of computer"]
    }

        if degree:
            allowed = degree_keywords.get(degree, [degree])
            if not any(k in edu_text for k in allowed):
                continue


    # ---------- SKILL MATCH (PARTIAL OK) ----------
        resume_skills = [s.lower() for s in r.get("skills", [])]

        matched_skills = [s for s in skills if s in resume_skills]
        if skills and len(matched_skills) == 0:
            continue


    # ---------- ATS SCORE ----------
        ats_score = r.get("ats_score", 0)
        if ats_score < min_ats:
            continue


    # ---------- AUTO SHORTLIST ----------
        resumes_collection.update_one(
            {"_id": r["_id"]},
            {"$set": {"status": "shortlisted"}}
        )

        shortlisted_count += 1


    if shortlisted_count == 0:
        flash("⚠️ No candidates matched the given criteria")
    else:
        flash(f"✅ {shortlisted_count} candidates shortlisted using ATS + JD")

    return redirect("/recruiter-dashboard")

@app.route("/recruiter/analysis/<resume_id>")
def recruiter_analysis(resume_id):
    if session.get("role") != "Recruiter":
        return redirect("/login")

    resume = resumes_collection.find_one({"_id": ObjectId(resume_id)})

    if not resume:
        flash("Resume not found")
        return redirect("/recruiter-dashboard")

    return render_template(
        "recruiter/analysis.html",
        resume=resume
    )


@app.route("/update-status", methods=["POST"])
def update_status():
    if session.get("role") != "Recruiter":
        return redirect("/login")

    resume_id = request.form.get("resume_id")
    status = request.form.get("status")

    resumes_collection.update_one(
        {"_id": ObjectId(resume_id)},
        {"$set": {"status": status}}
    )

    flash("✅ Candidate status updated")
    return redirect("/recruiter-dashboard")


@app.route("/export-csv")
def export_csv():
    if session.get("role") != "Recruiter":
        return redirect("/login")

    data = session.get("ranked_candidates", [])
    if not data:
        flash("Nothing to export")
        return redirect("/recruiter-dashboard")

    def generate():
        yield "Resume,ATS Score,Status\n"
        for c in data:
            yield f"{c['filename']},{c['ats_score']},{c['status']}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=ranked_candidates.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)
