import os
import re
import asyncio
import time
from pathlib import Path
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.thumb_manager import download_thumb
from bot.state import downloads
from bot.media_info import get_media_info
from bot.helpers import suppress_stdout, progress_bar
from bot.usage_tracker import log_usage
from bot.config import usage_collection   # ✅ NEW IMPORT

# ------------------- Default Thumbnail -------------------
DEFAULT_THUMB = download_thumb()


# ------------------- Safe Edit -------------------
async def safe_edit(message: Message, text: str, reply_markup=None):
    try:
        if message.text != text:
            await message.edit(text, reply_markup=reply_markup)
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            print("Safe edit error:", e)


# ------------------- Filename Cleaner -------------------
def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    patterns = [
        r'-\s*mkvCinemas\s*-?', r'-\s*GalaxyTV\s*-?', r'-\s*PrimeFix\s*-?',
        r'-\s*GalaxyRG\s*-?', r'www\.1TamilMV\.phd\s*-?', r'ww2\.TeluguFlix\.lol\s*-?',
        r'vegamovies\.to\s*-?', r'www\.1TamilBlasters\.art\s*-?', r'\[YTS\.MX\]',
        r'HQ', r'MoviesMod\.org', r'\[Toonworld4all\]', r'\[BollyFlix\]',
        r'_DEVENU_', r'MoviezVerse\.Net', r'SkymoviesHD\.actor', r'^\s*www\.[^ ]+\s*-\s*'
    ]
    for p in patterns:
        name = re.sub(p, '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'\s*-\s*', ' - ', name)
    return name.strip()


# ------------------- Upload File -------------------
# ✅ Corrected Upload File Function
async def upload_file(client, chat_id: int, file_path: str, status_message: Message, cancel_code: str, caption: str = None):
    original_name = Path(file_path).name
    clean_name = sanitize_filename(original_name).replace("_", " ")
    downloads[cancel_code]["uploading"] = True

    total_size = os.path.getsize(file_path)
    start_time = time.time()
    last_update = 0

    media_info_caption = get_media_info(file_path)
    final_caption = (
        caption
        or f"**{clean_name}**\n{media_info_caption}\n\n**Aᴅᴅᴇᴅ Bʏ: @Batmanlinkz**"
    )

    async def progress(current, total):
        nonlocal last_update
        now = time.time()
        if now - last_update >= 4:
            if cancel_code not in downloads or downloads[cancel_code]["cancelled"]:
                raise asyncio.CancelledError
            percent = min((current / max(total, total_size)) * 100, 100)
            elapsed = int(now - start_time)
            speed = current / elapsed if elapsed > 0 else 0
            cancel_button = InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{cancel_code}")]]
            )
            text = (
                f"⬆️ Uploading `{clean_name}`\n"
                f"{progress_bar(percent)}\n"
                f"Uploaded: {current/1024/1024:.2f} MB / {total_size/1024/1024:.2f} MB\n"
                f"Speed: {speed/1024/1024:.2f} MB/s | Elapsed: {elapsed}s"
            )
            await safe_edit(status_message, text, reply_markup=cancel_button)
            last_update = now

    thumb = DEFAULT_THUMB if DEFAULT_THUMB and os.path.exists(DEFAULT_THUMB) else None

    try:
        with suppress_stdout():
            await client.send_document(
                chat_id=chat_id,
                document=file_path,
                caption=final_caption,
                thumb=thumb,
                file_name=clean_name,
                progress=progress,
                force_document=True,
                disable_notification=True
            )

        await safe_edit(status_message, f"✅ Uploaded `{clean_name}`", reply_markup=None)

        # ✅ Correct usage logging
        try:
            await log_usage(total_size, "upload")
            print(f"📊 Logged upload usage: {clean_name} ({total_size / 1024 / 1024:.2f} MB)")
        except Exception as e:
            print(f"⚠️ Failed to log upload usage: {e}")

        # 🗑️ Delete uploaded file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ Deleted uploaded file: {file_path}")
            except Exception as e:
                print(f"⚠️ Failed to delete {file_path}: {e}")

    except asyncio.CancelledError:
        await safe_edit(status_message, f"❌ Upload cancelled: `{clean_name}`", reply_markup=None)
        return False

    finally:
        downloads[cancel_code]["uploading"] = False

    return True

