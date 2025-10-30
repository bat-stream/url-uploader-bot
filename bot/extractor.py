import os
import zipfile
import shutil
import asyncio
from pathlib import Path
from bot.helpers import sanitize_filename, random_folder_name
from bot.uploader import upload_file, safe_edit
from bot.state import downloads  # ✅ shared global state

async def extract_and_upload(client, channel_id: int, zip_path: str, status_message, cancel_code: str):
    """Extracts ZIP file and uploads each file sequentially."""

    if not zipfile.is_zipfile(zip_path):
        await safe_edit(status_message, f"❌ `{Path(zip_path).name}` is not a valid zip file.", reply_markup=None)
        downloads.pop(cancel_code, None)
        return

    extract_dir = Path("downloads") / random_folder_name()
    os.makedirs(extract_dir, exist_ok=True)
    await safe_edit(status_message, f"🗜 Extracting `{Path(zip_path).name}`...")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
    except Exception as e:
        await safe_edit(status_message, f"❌ Failed to extract zip: {e}", reply_markup=None)
        downloads.pop(cancel_code, None)
        return

    try:
        for f in sorted(extract_dir.rglob("*")):
            if f.is_file():
                safe_name = sanitize_filename(f.name)
                safe_path = f.parent / safe_name
                if f != safe_path:
                    f.rename(safe_path)

                uploaded = await upload_file(client, channel_id, str(safe_path), status_message, cancel_code)
                if uploaded and os.path.exists(safe_path):
                    try:
                        os.remove(safe_path)
                        print(f"🗑️ Deleted extracted file: {safe_path}")
                    except Exception as e:
                        print(f"⚠️ Could not delete extracted file {safe_path}: {e}")
                await asyncio.sleep(0)

    finally:
        # Always cleanup extracted folder and original zip
        try:
            shutil.rmtree(extract_dir, ignore_errors=True)
            print(f"🧹 Removed extract directory: {extract_dir}")
        except Exception as e:
            print(f"⚠️ Failed to delete extract directory: {e}")

        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
                print(f"🗑️ Deleted zip file: {zip_path}")
            except Exception as e:
                print(f"⚠️ Failed to delete zip file: {e}")

    if cancel_code in downloads:
        await safe_edit(status_message, "✅ Zip extracted and all files uploaded successfully.", reply_markup=None)
        downloads.pop(cancel_code)
