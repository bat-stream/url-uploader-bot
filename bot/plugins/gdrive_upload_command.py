# bot/plugins/gdrive_upload_command.py
import os
import asyncio
import aiohttp
from pathlib import Path
from pyrogram import filters
from pyrogram.types import Message
import urllib.parse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from bot.config import (
    ADMIN_ID, GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET,
    GDRIVE_REFRESH_TOKEN, GDRIVE_FOLDER_ID,
    GDRIVE_INDEX_LINK
)
from bot.uploader import safe_edit, progress_bar

downloads_path = Path("downloads")
os.makedirs(downloads_path, exist_ok=True)

# ------------------- Download File -------------------
async def download_file(url: str, dest_path: Path, status_msg: Message):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB
            with open(dest_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(chunk_size):
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = min(downloaded / total * 100, 100) if total else 0
                    text = (
                        f"⬇️ Downloading `{dest_path.name}`\n"
                        f"{progress_bar(percent)}\n"
                        f"Downloaded: {downloaded/1024/1024:.2f} MB "
                        f"of {total/1024/1024:.2f} MB"
                    )
                    await safe_edit(status_msg, text)

# ------------------- Upload to Google Drive -------------------
async def upload_to_gdrive(file_path: Path, status_msg: Message):
    creds = Credentials(
        token=None,
        refresh_token=GDRIVE_REFRESH_TOKEN,
        client_id=GDRIVE_CLIENT_ID,
        client_secret=GDRIVE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )

    service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': file_path.name,
        'parents': [GDRIVE_FOLDER_ID]
    }

    media = MediaFileUpload(str(file_path), resumable=True)
    request = service.files().create(body=file_metadata, media_body=media, fields='id,name')

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            percent = int(status.progress() * 100)
            text = (
                f"⬆️ Uploading `{file_path.name}`\n"
                f"{progress_bar(percent)}\n"
                f"Uploaded: {percent}%"
            )
            await safe_edit(status_msg, text)
    return response['id'], file_path.name

# ------------------- Register Command -------------------
def register_gdrive_upload(app):
    @app.on_message(filters.command("gdupload") & filters.private)
    async def gdupload_handler(client, message: Message):
        if str(message.from_user.id) != str(ADMIN_ID):
            await message.reply("🚫 Not authorized.")
            return

        if len(message.command) < 2:
            await message.reply("⚠️ Provide a URL to upload.")
            return

        url = message.command[1]
        file_name = Path(url).name
        file_path = downloads_path / file_name
        status_msg = await message.reply(f"⬇️ Starting download: `{file_name}`")

        # Download
        try:
            await download_file(url, file_path, status_msg)
        except Exception as e:
            await safe_edit(status_msg, f"❌ Failed to download file:\n{e}")
            return

        # Upload
        await safe_edit(status_msg, f"⬆️ Uploading `{file_name}` to Google Drive...")
        try:
            file_id, uploaded_name = await upload_to_gdrive(file_path, status_msg)

            # Encode properly for URLs
            encoded_name = urllib.parse.quote(uploaded_name, safe='')
            direct_link = f"{GDRIVE_INDEX_LINK}{encoded_name}"
            view_link = f"{direct_link}?a=view"

            await safe_edit(
                status_msg,
                f"✅ Uploaded `{uploaded_name}` successfully!\n\n"
                f"🔗 Direct Link: {direct_link}\n"
                f"👁 View Link: {view_link}"
            )

            # Delete local file
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            await safe_edit(status_msg, f"❌ Error uploading: {e}")
