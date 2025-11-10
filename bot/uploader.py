import os
import re
import asyncio
import time
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List, Dict

from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.thumb_manager import download_thumb
from bot.state import downloads
from bot.media_info import get_media_info
from bot.helpers import suppress_stdout, progress_bar
from bot.usage_tracker import log_usage
from bot.config import usage_collection

# ---------- default thumb ----------
DEFAULT_THUMB = download_thumb()

# ---------- language mapping ----------
LANG_MAP: Dict[str, str] = {
    "en": "English", "eng": "English",
    "hi": "Hindi", "hin": "Hindi",
    "ta": "Tamil", "tam": "Tamil",
    "te": "Telugu", "tel": "Telugu",
    "kn": "Kannada", "kan": "Kannada",
    "ml": "Malayalam", "mal": "Malayalam",
    "bn": "Bengali", "ben": "Bengali",
    "mr": "Marathi", "mar": "Marathi",
    "gu": "Gujarati", "guj": "Gujarati",
    "pa": "Punjabi", "pan": "Punjabi",
    "ur": "Urdu", "urd": "Urdu",
    "fr": "French", "fra": "French",
    "es": "Spanish", "spa": "Spanish",
    "de": "German", "ger": "German",
    "pt": "Portuguese", "por": "Portuguese",
    "ru": "Russian", "rus": "Russian",
    "ja": "Japanese", "jpn": "Japanese",
    "ko": "Korean", "kor": "Korean",
    "zh": "Chinese", "chi": "Chinese",
}

def code_to_full_language(code: Optional[str]) -> str:
    if not code:
        return "Unknown"
    c = str(code).strip().lower()
    if not c or c in ("und", "unknown"):
        return "Unknown"
    if c in LANG_MAP:
        return LANG_MAP[c]
    if len(c) >= 2 and c[:2] in LANG_MAP:
        return LANG_MAP[c[:2]]
    return c.capitalize()

# ---------- safe edit ----------
async def safe_edit(message: Message, text: str, reply_markup=None):
    try:
        if message.text != text:
            await message.edit(text, reply_markup=reply_markup)
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            print("Safe edit error:", e)

# ---------- filename sanitizer ----------
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

# ---------- pymediainfo probe ----------
def probe_streams(file_path: str):
    """
    Return lists of audio and subtitle stream info in order.
    Each item: {'index': int (1-based within type), 'language': str or None}
    """
    try:
        from pymediainfo import MediaInfo
    except Exception as e:
        print("pymediainfo unavailable:", e)
        return [], []
    try:
        mi = MediaInfo.parse(file_path)
    except Exception as e:
        print("pymediainfo parse failed:", e)
        return [], []

    audio_streams = []
    subtitle_streams = []
    a_idx = 0
    s_idx = 0
    for track in mi.tracks:
        if track.track_type == "Audio":
            a_idx += 1
            lang = getattr(track, "language", None) or getattr(track, "language_code", None) or None
            audio_streams.append({"index": a_idx, "language": lang})
        elif track.track_type == "Text":  # subtitles appear as Text
            s_idx += 1
            lang = getattr(track, "language", None) or getattr(track, "language_code", None) or None
            subtitle_streams.append({"index": s_idx, "language": lang})
    return audio_streams, subtitle_streams

# ---------- mkvpropedit writer (all tracks) ----------
def is_mkv(file_path: str) -> bool:
    return Path(file_path).suffix.lower() == ".mkv"

def write_mkv_metadata_all(file_path: str,
                           global_title: Optional[str],
                           video_name: Optional[str],
                           audio_streams: List[Dict],
                           subtitle_streams: List[Dict],
                           default_sub_index: Optional[int] = None) -> bool:
    """
    Use mkvpropedit to set container title, video name, every audio/sub title name,
    and mark one subtitle track as default (flag-default=1). If default_sub_index
    is None, it won't explicitly change default flags (but still sets names).
    """
    if not shutil.which("mkvpropedit"):
        print("mkvpropedit not found on PATH. Install mkvtoolnix.")
        return False

    cmd = ["mkvpropedit", file_path]

    if global_title:
        cmd += ["--set", f"title={global_title}"]

    if video_name:
        cmd += ["--edit", "track:v1", "--set", f"name={video_name}"]

    for a in audio_streams:
        idx = a.get("index", 1)
        lang_code = a.get("language")
        lang_full = code_to_full_language(lang_code)
        name = f"@BatmanLinkz-{lang_full}"
        cmd += ["--edit", f"track:a{idx}", "--set", f"name={name}"]

    # For subtitles: set name and default flag (0 or 1), if default_sub_index provided
    for s in subtitle_streams:
        idx = s.get("index", 1)
        lang_code = s.get("language")
        lang_full = code_to_full_language(lang_code)
        name = f"@BatmanLinkz-{lang_full}"
        cmd += ["--edit", f"track:s{idx}", "--set", f"name={name}"]
        if default_sub_index is not None:
            # set default flag: 1 for the chosen default subtitle, 0 for others
            flag = "1" if idx == default_sub_index else "0"
            cmd += ["--edit", f"track:s{idx}", "--set", f"flag-default={flag}"]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ mkvpropedit applied to all audio/subtitle tracks (default subtitle set).")
        return True
    except subprocess.CalledProcessError as e:
        print("⚠️ mkvpropedit failed:", e)
        return False
    except Exception as e:
        print("⚠️ mkvpropedit unexpected error:", e)
        return False


# ---------- helper: create simple SRT ----------
def create_single_srt(text: str, out_path: str, duration_seconds: int = 10):
    """
    Create a very simple single-entry SRT file that displays `text`
    from 00:00:00,000 to duration_seconds (max 10s default).
    """
    if duration_seconds < 1:
        duration_seconds = 10
    # format times
    start = "00:00:00,000"
    end_h = duration_seconds // 3600
    end_m = (duration_seconds % 3600) // 60
    end_s = duration_seconds % 60
    end = f"{end_h:02d}:{end_m:02d}:{end_s:02d},000"
    content = f"1\n{start} --> {end}\n{text}\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path

# ---------- main upload ----------
async def upload_file(client,
                      chat_id: int,
                      file_path: str,
                      status_message: Message,
                      cancel_code: str,
                      caption: str = None,
                      prefer_metadata: bool = True,
                      add_cover: bool = True,
                      add_subtitle_text: bool = True,
                      subtitle_text: str = "Join Now @BatmanLinkz Telegram",
                      subtitle_duration_seconds: int = 10):
    """
    Upload file and attempt to write metadata for MKV files.
    - Adds cover (thumbnail) as attachment if add_cover True and thumbnail present.
    - Adds a subtitle .srt track containing `subtitle_text` if add_subtitle_text True.
    - Edits all audio & subtitle track names to include full language names.
    """

    original_name = Path(file_path).name
    basename = Path(file_path).stem
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
            if cancel_code not in downloads or downloads[cancel_code].get("cancelled"):
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

    upload_path = file_path
    temp_files = []

    try:
        if prefer_metadata and is_mkv(file_path):
            # initial probe for existing streams
            audio_streams, subtitle_streams = probe_streams(file_path)

            # prepare names
            global_title = f"@BatmanLinkz - {basename}"
            video_name = f"Join Now @BatmanLinkz - {clean_name}"

            # make a cheap temp copy via hardlink (so we don't touch original). If hardlink fails, copy.
            parent = Path(file_path).parent
            tmp1 = str(parent / f"{basename}.meta.tmp.mkv")
            try:
                if not os.path.exists(tmp1):
                    try:
                        os.link(file_path, tmp1)
                    except Exception:
                        shutil.copy2(file_path, tmp1)
                temp_files.append(tmp1)
            except Exception as e:
                print("Could not create temp hardlink/copy:", e)
                tmp1 = file_path  # fallback to original

            # Optionally create SRT file
            srt_path = None
            if add_subtitle_text:
                # place srt in temp dir
                fd, srt_path = tempfile.mkstemp(suffix=".srt", prefix=f"{basename}_sub_")
                os.close(fd)
                create_single_srt(subtitle_text, srt_path, duration_seconds=subtitle_duration_seconds)
                temp_files.append(srt_path)

            # Decide an output path for mkvmerge
            merged_out = str(parent / f"{basename}.meta.merged.mkv")
            # build mkvmerge command
            if shutil.which("mkvmerge") is None:
                print("mkvmerge not found on PATH — skipping merge step.")
                merged_success = False
            else:
                cmd = ["mkvmerge", "-o", merged_out, tmp1]
                # if we have an srt to add, append it (language set to eng by default)
                if srt_path:
                    # append srt; set language to 'eng' for the added file (user can change)
                    cmd += [srt_path, "--language", "0:eng"]
                # if we have a cover/thumbnail, attach it
                if add_cover and thumb and os.path.exists(thumb):
                    # mkvmerge supports attachment flags anywhere; add after inputs
                    cmd += ["--attachment-name", "cover.jpg", "--attach-file", thumb]
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    merged_success = True
                    temp_files.append(merged_out)
                    upload_path = merged_out
                    total_size = os.path.getsize(upload_path)
                    print("✅ mkvmerge created merged file with attachments/subs:", merged_out)
                except subprocess.CalledProcessError as e:
                    print("⚠️ mkvmerge failed:", e)
                    merged_success = False
                    # cleanup merged file if partially created
                    if os.path.exists(merged_out):
                        try:
                            os.remove(merged_out)
                        except Exception:
                            pass
                    upload_path = tmp1 if os.path.exists(tmp1) else file_path

            # after mkvmerge, re-probe the file to get up-to-date tracks (this includes added subtitle)
            # re-probe the file to get up-to-date tracks (this includes added subtitle)
            try:
                audio_streams_after, subtitle_streams_after = probe_streams(upload_path)

                # determine which subtitle was added:
                # if we had subtitle_streams (before) and subtitle_streams_after (after),
                # the new subtitle(s) are at the tail of subtitle_streams_after.
                default_sub_index = None
                try:
                    before_count = len(subtitle_streams)  # subtitle_streams is the list from before mkvmerge
                    after_count = len(subtitle_streams_after)
                    if after_count > before_count:
                        # pick the newly added subtitle(s). Most common: pick the last one.
                        default_sub_index = subtitle_streams_after[-1].get("index")
                        print(f"Detected newly added subtitle track index: {default_sub_index}")
                    else:
                        # fallback: if we intended to add a subtitle but counts didn't increase,
                        # try to find a subtitle with language 'eng' and prefer that
                        for s in subtitle_streams_after:
                            lang = s.get("language")
                            if lang and lang.lower().startswith("en"):
                                default_sub_index = s.get("index")
                                break
                except Exception as e:
                    print("Could not determine default subtitle index:", e)
                    default_sub_index = None

                # Now apply mkvpropedit to set names and default subtitle flag
                success_edit = write_mkv_metadata_all(
                    upload_path,
                    global_title=global_title,
                    video_name=video_name,
                    audio_streams=audio_streams_after or audio_streams,
                    subtitle_streams=subtitle_streams_after or subtitle_streams,
                    default_sub_index=default_sub_index
                )
                if not success_edit:
                    print("⚠️ mkvpropedit failed to write names/default flags; continuing with file without those changes.")
            except Exception as e:
                print("⚠️ Re-probe or mkvpropedit failed:", e)


    except Exception as e:
        print("Metadata preparation failed, continuing without metadata:", e)
        upload_path = file_path

    # ---------- perform upload ----------
    try:
        with suppress_stdout():
            await client.send_document(
                chat_id=chat_id,
                document=upload_path,
                caption=final_caption,
                thumb=thumb,
                file_name=clean_name,
                progress=progress,
                force_document=True,
                disable_notification=True
            )

        await safe_edit(status_message, f"✅ Uploaded `{clean_name}`", reply_markup=None)

        # log usage
        try:
            await log_usage("upload", os.path.getsize(upload_path))
            print(f"📊 Logged upload usage: {clean_name} ({os.path.getsize(upload_path) / 1024 / 1024:.2f} MB)")
        except Exception as e:
            print("⚠️ Failed to log upload usage:", e)

        # cleanup temp files and original if desired
        try:
            for t in temp_files:
                if t and os.path.exists(t):
                    try:
                        os.remove(t)
                    except Exception:
                        pass

            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Deleted uploaded file: {file_path}")
        except Exception as e:
            print("⚠️ Failed to delete files after upload:", e)

    except asyncio.CancelledError:
        await safe_edit(status_message, f"❌ Upload cancelled: `{clean_name}`", reply_markup=None)
        return False

    finally:
        downloads[cancel_code]["uploading"] = False

    return True
