from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["resume_screening"]

users_collection = db["users"]
resumes_collection = db["resumes"]
jobs_collection = db["jobs"]
