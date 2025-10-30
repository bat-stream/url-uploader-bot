import re, random, asyncio, aiohttp, socket, time
import os
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import ADMIN_ID, CHANNEL_ID, downloads_path
from bot.helpers import is_admin, sanitize_filename, get_filename_from_url
from bot.downloader import monitor_download
from bot.uploader import safe_edit, downloads
from bot.aria2_setup import aria2

# ------------------- Callback Handler -------------------
def register_callbacks(app):
    @app.on_callback_query()
    async def handle_cancel(client, callback_query):
        data = callback_query.data
        if not data.startswith("cancel_"): 
            return
        cancel_code = data.split("_", 1)[1]
        if cancel_code in downloads:
            downloads[cancel_code]["cancelled"] = True
            await callback_query.answer("❌ Cancel requested!")
            status_msg = downloads[cancel_code]["status_msg"]
            await safe_edit(status_msg, f"❌ Cancel requested by user", reply_markup=None)
        else:
            await callback_query.answer("❌ Already completed or invalid.", show_alert=True)

# ------------------- Command Handlers -------------------
def register_commands(app):
    @app.on_message(filters.command("start") & filters.private)
    async def start_handler(client, message: Message):
        if not is_admin(message.from_user.id, ADMIN_ID):
            await message.reply("🚫 Not authorized.")
            return
        await message.reply("👋 Send a file URL. Append `-e` to extract zip or use `-n newname` to rename.")

    @app.on_message(filters.command("speedtest") & filters.private)
    async def speedtest_handler(client, message: Message):
        if not is_admin(message.from_user.id, ADMIN_ID):
            await message.reply("🚫 Not authorized.")
            return

        status_msg = await message.reply("⏳ Running full speedtest... This may take 30-60 seconds.")

        async def download_speed_test():
            url = "https://speed.hetzner.de/100MB.bin"
            start = time.time()
            downloaded = 0
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        while True:
                            chunk = await resp.content.read(1024 * 1024)
                            if not chunk:
                                break
                            downloaded += len(chunk)
            except:
                return 0
            elapsed = time.time() - start
            return (downloaded * 8 / 1_000_000) / max(elapsed, 0.001)

        async def upload_speed_test():
            url = "https://httpbin.org/post"
            data = b"x" * (10 * 1024 * 1024)
            start = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=data) as resp:
                        await resp.text()
            except:
                return 0
            elapsed = time.time() - start
            return (len(data) * 8 / 1_000_000) / max(elapsed, 0.001)

        async def ping_test(host="8.8.8.8", port=53, timeout=2):
            start = time.time()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((host, port))
                sock.close()
            except:
                return None
            return int((time.time() - start) * 1000)

        async def get_ip_info():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://ipinfo.io/json") as resp:
                        data = await resp.json()
                        ip = data.get("ip", "Unknown")
                        org = data.get("org", "Unknown")
                        city = data.get("city", "")
                        country = data.get("country", "")
                        return f"{ip} | {org} | {city}, {country}"
            except:
                return "Unknown"

        try:
            download, upload, ping, ip_info = await asyncio.gather(
                download_speed_test(),
                upload_speed_test(),
                ping_test(),
                get_ip_info()
            )
            text = (
                f"⚡ **Speedtest Results:**\n\n"
                f"📥 Download: {download:.2f} Mbps\n"
                f"📤 Upload: {upload:.2f} Mbps\n"
                f"🏓 Ping: {ping if ping else 'N/A'} ms\n"
                f"🌐 IP / ISP / Location: {ip_info}"
            )
            await safe_edit(status_msg, text)
        except Exception as e:
            await safe_edit(status_msg, f"❌ Speedtest failed: {e}")



# ------------------- URL Handler -------------------
def register_url_handler(app):
    @app.on_message(filters.private & filters.text)
    async def url_handler(client, message: Message):
        if not is_admin(message.from_user.id, ADMIN_ID):
            await message.reply("🚫 Not authorized.")
            return

        text = message.text.strip()
        extract_zip = False
        new_filename = None

        if text.endswith(" -e"):
            extract_zip = True
            text = text[:-3].strip()

        rename_match = re.search(r'\s+-n\s+(.+)$', text)
        if rename_match:
            new_filename = rename_match.group(1).strip()
            text = text[:rename_match.start()].strip()

        url = text
        filename = sanitize_filename(new_filename) if new_filename else await get_filename_from_url(url)
        file_path = downloads_path / filename
        status_message = await message.reply(f"📥 Starting download: `{filename}`")

        download = aria2.add_uris([url], {"dir": str(downloads_path), "out": filename})
        cancel_code = str(random.randint(1000000, 9999999))
        downloads[cancel_code] = {
            "gid": download.gid,
            "cancelled": False,
            "file_path": str(file_path),
            "status_msg": status_message,
            "uploading": False
        }

        asyncio.create_task(monitor_download(cancel_code, client, aria2, CHANNEL_ID))
