# bot/plugins/restart_command.py
import requests
from pyrogram import filters
from pyrogram.types import Message
from bot.config import ADMIN_ID, RENDER_API_KEY, RENDER_SERVICE_ID  # ✅ import from config

def restart_service():
    """Uses Render API to restart the current service."""
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        return "❌ Missing Render API credentials."

    url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/restart"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers)
        if response.status_code in (200, 202):
            return "🔄 Service restart initiated successfully on Render!"
        else:
            return f"⚠️ Failed to restart.\nStatus: {response.status_code}\n{response.text}"
    except Exception as e:
        return f"❌ Error: {e}"


def register_restart_command(app):
    @app.on_message(filters.command("restart") & filters.private)
    async def restart_handler(client, message: Message):
        if str(message.from_user.id) != str(ADMIN_ID):
            await message.reply("🚫 Not authorized.")
            return

        await message.reply("🔁 Restarting service on Render...")
        result = restart_service()
        await message.reply(result)
