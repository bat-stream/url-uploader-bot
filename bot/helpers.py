import os, re, random, sys, contextlib, socket, asyncio, aiohttp
from pathlib import Path
from urllib.parse import urlparse, unquote

def is_admin(user_id: int, admin_id: int) -> bool:
    return user_id == admin_id

def progress_bar(percent: float, length: int = 12) -> str:
    filled = int(length * percent / 100)
    bar = "■" * filled + "□" * (length - filled)
    return f"[{bar}] {percent:.2f}%"

import re

def sanitize_filename(name: str) -> str:
    """
    Cleans movie filenames while preserving readability.
    Removes site tags, replaces unsafe characters, and normalizes spacing.
    """

    # --- Remove common site or release group tags ---
    site_patterns = (
        r'mkvCinemas|GalaxyTV|PrimeFix|GalaxyRG|www\.1TamilMV\.phd|'
        r'ww2\.TeluguFlix\.lol|vegamovies\.to|www\.1TamilBlasters\.art|'
        r'\[YTS\.MX\]|HQ|MoviesMod\.org|\[Toonworld4all\]|\[BollyFlix\]|'
        r'_DEVENU_|MoviezVerse\.Net|SkymoviesHD\.actor'
    )
    name = re.sub(site_patterns, '', name, flags=re.IGNORECASE)

    # --- Remove forbidden filesystem characters ---
    name = re.sub(r'[<>:"/\\|?*]', '', name)

    # --- Replace + and other rare unsafe symbols with underscore ---
    name = re.sub(r'[+]', '_', name)

    # --- Remove leftover duplicate hyphens or spaces ---
    name = re.sub(r'\s*-\s*', ' - ', name)
    name = re.sub(r'\s+', ' ', name).strip()

    # --- Remove leading "www.sitename - " prefixes if still there ---
    name = re.sub(r'^\s*www\.[^ ]+\s*-\s*', '', name, flags=re.IGNORECASE)

    # --- Normalize underscores/spaces if excessive ---
    name = re.sub(r'_+', '_', name)

    return name


def random_folder_name(length=5) -> str:
    return str(random.randint(10**(length-1), 10**length - 1))

async def get_filename_from_url(url: str) -> str:
    path = urlparse(url).path
    name = Path(unquote(path)).name
    if name:
        return sanitize_filename(name)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True) as resp:
                cd = resp.headers.get("Content-Disposition")
                if cd:
                    match = re.search(r'filename="?([^"]+)"?', cd)
                    if match:
                        return sanitize_filename(match.group(1))
    except:
        pass
    ext = Path(path).suffix or ".file"
    return f"{random_folder_name()}{ext}"

@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_out = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_out
