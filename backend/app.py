from flask import Flask, render_template, request, redirect, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import os

# ================= NLP =================
from backend.nlp.resume_parser import parse_resume
from backend.nlp.skill_extractor import extract_skills_from_sections
from backend.nlp.matcher import calculate_ats_score
from backend.nlp.feedback_engine import generate_ats_feedback
from backend.nlp.matcher import calculate_simple_ats

# ================= DB =================
from backend.db import users_collection, resumes_collection, jobs_collection, applications_collection

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

@app.route("/")
def landing():
    return render_template("landing.html")


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
# CANDIDATE - VIEW RECRUITERS
# ======================================================

@app.route("/candidate/recruiters")
def candidate_recruiters():
    if session.get("role") != "Candidate":
        return redirect("/login")

    recruiters = list(
        users_collection.find({"role": "Recruiter"})
    )

    return render_template(
        "candidate/recruiters.html",
        recruiters=recruiters
    )

@app.route("/candidate/recruiter/<recruiter_id>")
def view_recruiter_jobs(recruiter_id):

    if session.get("role") != "Candidate":
        return redirect("/login")

    try:
        recruiter_obj_id = ObjectId(recruiter_id)
    except:
        flash("Invalid recruiter ID")
        return redirect("/candidate/recruiters")

    recruiter = users_collection.find_one({"_id": recruiter_obj_id})

    if not recruiter:
        flash("Recruiter not found")
        return redirect("/candidate/recruiters")

    candidate_id = session.get("user_id")

    jobs = list(
        jobs_collection.find({"created_by": recruiter_id})
        .sort("created_at", -1)
    )

    # 🔥 Attach application status for each job
    for job in jobs:
        application = applications_collection.find_one({
            "job_id": str(job["_id"]),
            "candidate_id": candidate_id
        })

        if application:
            job["application_status"] = application.get("status", "pending")
        else:
            job["application_status"] = None

    return render_template(
        "candidate/recruiter_jobs.html",
        recruiter=recruiter,
        jobs=jobs
    )


# ======================================================
# CANDIDATE → APPLY TO JOB
# ======================================================

@app.route("/candidate/apply/<job_id>", methods=["GET", "POST"])
def candidate_apply(job_id):

    if session.get("role") != "Candidate":
        return redirect("/login")

    candidate_id = session.get("user_id")

    # 1️⃣ Get Job
    job = jobs_collection.find_one({"_id": ObjectId(job_id)})
    if not job:
        flash("Job not found")
        return redirect("/candidate/recruiters")

    # 2️⃣ Get Candidate Resumes
    resumes = list(
        resumes_collection.find({"uploaded_by": candidate_id})
        .sort("uploaded_at", -1)
    )

    if request.method == "POST":
        resume_id = request.form.get("resume_id")

        if not resume_id:
            flash("Please select a resume")
            return redirect(request.url)

        # 3️⃣ Prevent duplicate apply
        existing = applications_collection.find_one({
            "job_id": job_id,
            "candidate_id": candidate_id
        })

        if existing:
            flash("You already applied to this job")
            return redirect(request.url)

        # 4️⃣ Insert Application
        applications_collection.insert_one({
            "job_id": job_id,
            "candidate_id": candidate_id,
            "resume_id": resume_id,
            "match_score": 0,
            "status": "pending",
            "applied_at": datetime.utcnow()
        })

        flash("Application submitted successfully")
        return redirect(f"/candidate/recruiter/{job['created_by']}")

    return render_template(
        "candidate/apply_job.html",
        job=job,
        resumes=resumes
    )

# ======================================================
# RECRUITER SIDE (FINAL & STABLE)
# ======================================================

@app.route("/recruiter-dashboard")
def recruiter_dashboard():
    if session.get("role") != "Recruiter":
        return redirect("/login")

    recruiter_id = session.get("user_id")

    # Get recruiter jobs
    recruiter_jobs = list(
        jobs_collection.find({"created_by": recruiter_id})
    )

    job_ids = [str(job["_id"]) for job in recruiter_jobs]

    total = applications_collection.count_documents({
        "job_id": {"$in": job_ids}
    })

    shortlisted = applications_collection.count_documents({
        "job_id": {"$in": job_ids},
        "status": "shortlisted"
    })

    rejected = applications_collection.count_documents({
        "job_id": {"$in": job_ids},
        "status": "rejected"
    })

    pending = applications_collection.count_documents({
        "job_id": {"$in": job_ids},
        "status": "pending"
    })

    return render_template(
        "recruiter_dashboard.html",
        total=total,
        shortlisted=shortlisted,
        rejected=rejected,
        pending=pending
    )

# ======================================================
# RECRUITER → VIEW JOB APPLICANTS (SECURE)
# ======================================================

@app.route("/recruiter/job/<job_id>")
def recruiter_job_applicants(job_id):

    if session.get("role") != "Recruiter":
        return redirect("/login")

    recruiter_id = session.get("user_id")

    try:
        job = jobs_collection.find_one({
            "_id": ObjectId(job_id),
            "created_by": recruiter_id
        })
    except:
        flash("Invalid job ID")
        return redirect("/recruiter/jobs")

    if not job:
        flash("Job not found")
        return redirect("/recruiter/jobs")

    applications = list(
        applications_collection.find({"job_id": job_id})
    )

    enriched_apps = []

    for app_doc in applications:

        try:
            candidate = users_collection.find_one({
                "_id": ObjectId(app_doc.get("candidate_id"))
            })

            resume = resumes_collection.find_one({
                "_id": ObjectId(app_doc["resume_id"])
        })

            enriched_apps.append({
                "application_id": str(app_doc["_id"]),
                "candidate_name": candidate.get("name") if candidate else "Unknown",
                "candidate_email": candidate.get("email") if candidate else "",
                "resume_filename": resume.get("filename") if resume else "",
                "ats_score": resume.get("ats_score", 0) if resume else 0,
                "summary": resume.get("summary", "") if resume else "",
                "skills": resume.get("skills", []) if resume else [],
                "status": app_doc.get("status", "pending"),
                "applied_at": app_doc.get("applied_at")
            })

        except:
            continue

    return render_template(
        "recruiter/manage_applicants.html",
        job=job,
        applications=enriched_apps
    )


@app.route("/recruiter/update-application-status", methods=["POST"])
def update_application_status():

    if session.get("role") != "Recruiter":
        return redirect("/login")

    application_id = request.form.get("application_id")
    status = request.form.get("status")

    app_doc = applications_collection.find_one({
        "_id": ObjectId(application_id)
    })

    if not app_doc:
        flash("Application not found")
        return redirect("/recruiter-dashboard")

    # 1️⃣ Update application status
    applications_collection.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"status": status}}
    )

    # 2️⃣ ALSO update resume status (so dashboard counts work)
    resumes_collection.update_one(
        {"_id": ObjectId(app_doc["resume_id"])},
        {"$set": {"status": status}}
    )

    flash(f"Candidate {status.capitalize()} successfully")

    return redirect(request.referrer)

# ======================================================
# RECRUITER JOB MANAGEMENT (PHASE 2)
# ======================================================

@app.route("/recruiter/jobs")
def recruiter_jobs():
    if session.get("role") != "Recruiter":
        return redirect("/login")

    recruiter_id = session.get("user_id")

    jobs = list(
        jobs_collection.find({"created_by": recruiter_id})
    )


    # Count applicants per job
    for job in jobs:
        applicant_count = applications_collection.count_documents({
            "job_id": str(job["_id"])
        })
        job["applicant_count"] = applicant_count

    return render_template("recruiter/jobs.html", jobs=jobs)

@app.route("/recruiter/create-job", methods=["GET", "POST"])
def create_job():
    if session.get("role") != "Recruiter":
        return redirect("/login")

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        required_skills = request.form.get("skills")
        degree = request.form.get("degree")

        jobs_collection.insert_one({
            "title": title,
            "description": description,
            "required_skills": [s.strip().lower() for s in required_skills.split(",") if s.strip()],
            "degree": degree.lower(),
            "created_by": session.get("user_id"),
            "created_at": datetime.utcnow()
        })

        flash("✅ Job created successfully")
        return redirect("/recruiter/jobs")

    return render_template("recruiter/create_job.html")

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

