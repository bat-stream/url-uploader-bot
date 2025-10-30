import datetime
from bot.config import usage_collection  # use the shared collection

def get_month_key():
    now = datetime.datetime.utcnow()
    return f"{now.year}-{now.month:02d}"

async def log_usage(action: str, bytes_used: int):
    month_key = get_month_key()
    doc = await usage_collection.find_one({"month": month_key})

    if not doc:
        # Reset for new month
        await usage_collection.delete_many({})
        await usage_collection.insert_one({
            "month": month_key,
            "uploads": 0,
            "downloads": 0,
            "upload_bytes": 0,
            "download_bytes": 0,
            "last_reset": datetime.datetime.utcnow()
        })
        doc = await usage_collection.find_one({"month": month_key})

    update = {}
    if action == "upload":
        update = {"$inc": {"uploads": 1, "upload_bytes": bytes_used}}
    elif action == "download":
        update = {"$inc": {"downloads": 1, "download_bytes": bytes_used}}

    if update:
        await usage_collection.update_one({"month": month_key}, update)

async def get_usage_summary():
    month_key = get_month_key()
    doc = await usage_collection.find_one({"month": month_key})
    if not doc:
        return "📊 No usage data recorded yet."

    upload_gb = doc.get("upload_bytes", 0) / (1024**3)
    download_gb = doc.get("download_bytes", 0) / (1024**3)
    total_gb = upload_gb + download_gb

    return (
        f"📆 **Usage for {month_key}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⬆️ Uploaded Files: {doc.get('uploads', 0)}\n"
        f"⬇️ Downloaded Files: {doc.get('downloads', 0)}\n\n"
        f"📦 Upload Data: {upload_gb:.2f} GB\n"
        f"📡 Download Data: {download_gb:.2f} GB\n"
        f"💾 Total Bandwidth Used: {total_gb:.2f} GB\n\n"
        f"🕓 Last Reset: {doc.get('last_reset').strftime('%Y-%m-%d %H:%M UTC')}"
    )
