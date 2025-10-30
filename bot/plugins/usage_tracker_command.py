# bot/plugins/usage_tracker_command.py
from pyrogram import filters
from pyrogram.types import Message
from bot.usage_tracker import get_usage_summary  # ✅ Updated import
from bot.config import ADMIN_ID

def register_usage_tracker(app):
    @app.on_message(filters.command("usage") & filters.private)
    async def usage_handler(client, message: Message):
        if str(message.from_user.id) != str(ADMIN_ID):
            await message.reply("🚫 Not authorized.")
            return

        summary_text = await get_usage_summary()
        await message.reply(summary_text)
