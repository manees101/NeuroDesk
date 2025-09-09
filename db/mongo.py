from pymongo import MongoClient
import os

MONGO_URI = os.getenv("DB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "mydatabase")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Ensure indexes
try:
    db["users"].create_index("email", unique=True)
    db["password_reset_tokens"].create_index("token", unique=True)
    db["password_reset_tokens"].create_index("expires_at")
    db["email_logs"].create_index([("email", 1), ("created_at", -1)])
except Exception:
    # Index creation errors are non-fatal for runtime
    pass