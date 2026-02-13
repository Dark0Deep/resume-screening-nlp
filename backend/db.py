import os
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["resume_db"]

users_collection = db["users"]
resumes_collection = db["resumes"]
jobs_collection = db["jobs"]
applications_collection = db["applications"]
