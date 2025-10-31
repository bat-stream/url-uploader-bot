from bot.server import start_server
from bot.config import API_ID, API_HASH, BOT_TOKEN
from pyrogram import Client
import logging
from pathlib import Path
import shutil
import os

from bot.handlers import register_callbacks, register_commands, register_url_handler
from bot.plugins.usage_tracker_command import register_usage_tracker
from bot.plugins.restart_command import register_restart_command




# Silence Pyrogram logs
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# Create bot client
app = Client("url_upload_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Register handlers
register_callbacks(app)
register_commands(app)
register_usage_tracker(app)
register_restart_command(app) 
register_url_handler(app)


# 🧹 Clean downloads directory on startup
downloads_path = Path("downloads")
os.makedirs(downloads_path, exist_ok=True)

for item in downloads_path.iterdir():
    try:
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    except Exception as e:
        print(f"⚠️ Failed to remove {item}: {e}")

print("🧹 Cleaned old downloads on startup.")

if __name__ == "__main__":
    start_server()
    print("Starting bot...")
    app.run()
