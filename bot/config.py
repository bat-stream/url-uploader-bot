import os
from pathlib import Path
from dotenv import load_dotenv
import motor.motor_asyncio

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
THUMB_URL = os.getenv("THUMB_URL", "https://bat-cave.jkleecher.workers.dev/0:/image-2025-09-24-163452620.png")
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "url_uploader_bot")
GDRIVE_CLIENT_ID = os.getenv("GDRIVE_CLIENT_ID", "YOUR_CLIENT_ID_HERE")
GDRIVE_CLIENT_SECRET = os.getenv("GDRIVE_CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE")
GDRIVE_REFRESH_TOKEN = os.getenv("GDRIVE_REFRESH_TOKEN", "refresh_tocken")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "Folder_id")
GDRIVE_INDEX_LINK = os.getenv("GDRIVE_INDEX_LINK", "https://bat-cave.botzzz.workers.dev/1:/")
GDRIVE_REMOTE_NAME = "Folder1"  # name used for in-memory rclone remote


# MongoDB client & collection
if not MONGO_URL:
    raise ValueError("❌ Missing MONGO_URL in environment variables")

mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]
usage_collection = db["usage"]  # ✅ shared usage collection


downloads_path = Path("downloads")
os.makedirs(downloads_path, exist_ok=True)
