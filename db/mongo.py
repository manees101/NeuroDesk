from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os

MONGO_URI = os.getenv("DB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "mydatabase")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]