import os
import requests
from bot.config import THUMB_URL
from pathlib import Path

THUMB_PATH = Path("thumb.jpg")

def download_thumb():
    """
    Downloads the thumbnail from THUMB_URL (if defined) once at startup
    and returns the local file path.
    """
    if not THUMB_URL:
        print("⚠️ No thumbnail URL provided.")
        return None

    try:
        resp = requests.get(THUMB_URL, stream=True, timeout=10)
        if resp.status_code == 200:
            with open(THUMB_PATH, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            print(f"✅ Thumbnail downloaded to {THUMB_PATH}")
            return str(THUMB_PATH)
        else:
            print(f"❌ Failed to fetch thumbnail ({resp.status_code})")
    except Exception as e:
        print(f"❌ Thumbnail download error: {e}")

    return None
