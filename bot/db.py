import motor.motor_asyncio
import os

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise ValueError("❌ Missing MONGO_URL in environment variables")

# Use env variable or default to 'url_uploader_bot'
DB_NAME = os.getenv("MONGO_DB", "url_uploader_bot")

mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]
usage_collection = db["usage"]
