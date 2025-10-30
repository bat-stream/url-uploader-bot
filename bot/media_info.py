import re
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

LANGUAGE_MAP = {
    "en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
    "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "bn": "Bengali",
    "gu": "Gujarati", "pa": "Punjabi", "ja": "Japanese", "ko": "Korean",
    "zh": "Chinese", "fr": "French", "de": "German", "es": "Spanish",
    "it": "Italian", "ru": "Russian", "ar": "Arabic",
}

def map_language(code: str) -> str:
    return LANGUAGE_MAP.get(code.lower().strip(), code.capitalize()) if code else ""

def detect_quality(height: int) -> str:
    if height >= 2160: return "4K"
    if height >= 1440: return "2K"
    if height >= 1080: return "1080p"
    if height >= 720: return "720p"
    if height >= 480: return "480p"
    return f"{height}p"

def get_media_info(file_path: str) -> str:
    parser = createParser(file_path)
    if not parser: return "**Could not parse file**"
    metadata = extractMetadata(parser)
    if not metadata: return "**Could not extract metadata**"

    video_qualities = set()
    audios = []
    subtitles = set()
    duration_str = "Unknown"

    try:
        dur = metadata.get('duration').seconds if metadata.has('duration') else 0
        if dur:
            hours = dur // 3600
            minutes = (dur % 3600) // 60
            seconds = dur % 60
            duration_str = f"{hours}h{minutes}m{seconds}s" if hours else f"{minutes}m{seconds}s"
    except: pass

    lines = metadata.exportPlaintext()
    current_track = None
    for line in lines:
        line = line.strip()
        if line.startswith("Video stream"): current_track = "video"
        elif line.startswith("Audio stream"): current_track = "audio"
        elif line.startswith("Subtitle"): current_track = "subtitle"
        else:
            if current_track == "video":
                m = re.search(r"Image height:\s*(\d+)", line)
                if m: video_qualities.add(detect_quality(int(m.group(1))))
            elif current_track == "audio":
                m = re.search(r"Language:\s*(\w+)", line)
                if m: audios.append(map_language(m.group(1)))
            elif current_track == "subtitle":
                m = re.search(r"Language:\s*(\w+)", line)
                if m: subtitles.add(map_language(m.group(1)))

    video_text = ", ".join(sorted(video_qualities)) or "Unknown"
    audio_text = ", ".join(audios) if audios else "Unknown"
    subtitle_text = ", ".join(sorted(subtitles)) if subtitles else "None"

    return f"**🎬 {video_text} | ⏳ {duration_str}\n🔊 {audio_text}\n💬 {subtitle_text}**"
