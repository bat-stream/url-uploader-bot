# bot/downloader.py
import os
import asyncio
import zipfile
from pathlib import Path
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.uploader import upload_file, safe_edit
from bot.state import downloads
from bot.extractor import extract_and_upload
from bot.helpers import progress_bar
from bot.usage_tracker import log_usage
from bot.config import usage_collection   # ✅ Import bandwidth tracker


async def monitor_download(cancel_code: str, client, aria2, channel_id: int):
    """Monitors aria2 download progress, updates message, and triggers upload."""

    while cancel_code in downloads:
        try:
            gid = downloads[cancel_code]["gid"]
            status_msg = downloads[cancel_code]["status_msg"]
            download = aria2.get_download(gid)

            # Handle user cancellation
            if downloads[cancel_code].get("cancelled"):
                try:
                    aria2.remove([download], force=True, files=True)
                except Exception as e:
                    print(f"⚠️ Error removing aria2 task: {e}")
                await safe_edit(status_msg, "❌ Download cancelled by user.", reply_markup=None)
                downloads.pop(cancel_code, None)
                return

            total = download.total_length or 0
            done = download.completed_length
            percent = (done / total * 100) if total else 0
            percent = min(percent, 100)
            speed = download.download_speed / 1024 / 1024

            cancel_button = InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{cancel_code}")]]
            )

            text = (
                f"⬇️ `{Path(downloads[cancel_code]['file_path']).name}`\n"
                f"┃ {progress_bar(percent)}\n"
                f"┠ Processed: {done/1024/1024:.2f} MiB of {total/1024/1024:.2f} MiB\n"
                f"┠ Status: {download.status} | Speed: {speed:.2f} MB/s"
            )

            await safe_edit(status_msg, text, reply_markup=cancel_button)

            # ✅ When complete, handle upload or extraction
            if download.is_complete and done >= total:
                file_path = downloads[cancel_code]["file_path"]

                if not os.path.exists(file_path):
                    print(f"⚠️ File not found after download: {file_path}")
                    await safe_edit(status_msg, f"⚠️ File missing: `{Path(file_path).name}`", reply_markup=None)
                    downloads.pop(cancel_code, None)
                    return

                # ✅ Log download bandwidth to MongoDB
                try:
                    await log_usage(os.path.getsize(file_path), "download")
                    print(f"📊 Logged download usage for {file_path}")
                except Exception as e:
                    print(f"⚠️ Failed to log download usage: {e}")

                # Handle ZIP or direct upload
                if zipfile.is_zipfile(file_path):
                    await extract_and_upload(client, channel_id, file_path, status_msg, cancel_code)
                else:
                    uploaded = await upload_file(client, channel_id, file_path, status_msg, cancel_code)

                    if uploaded and os.path.exists(file_path):
                        # 🧹 Cleanup after upload
                        try:
                            os.remove(file_path)
                            print(f"🗑️ Deleted uploaded file: {file_path}")
                        except Exception as e:
                            print(f"⚠️ Failed to delete file after upload: {e}")

                    if cancel_code in downloads:
                        downloads.pop(cancel_code)
                return

        except Exception as e:
            print("Monitor error:", e)

        await asyncio.sleep(2)
