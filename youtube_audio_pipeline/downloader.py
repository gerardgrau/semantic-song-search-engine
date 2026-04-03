from __future__ import annotations

import os
import tempfile
import logging
import uuid
import time
from pathlib import Path

import yt_dlp

logger = logging.getLogger(__name__)

# Global "Circuit Breaker"
_COOKIES_ENABLED = True

def ensure_ram_path(ram_disk_path: str = "/dev/shm/yt_audio") -> Path:
    preferred = Path(ram_disk_path)
    if preferred.parent.exists():
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred

    fallback = Path(tempfile.gettempdir()) / "yt_audio"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def download_to_ram(
    url: str,
    ram_disk_path: str = "/dev/shm/yt_audio",
    cookies_path: str | None = None
) -> tuple[str, str | None, dict | None]:
    """
    Stealth Downloader with Client Rotation.
    Tries different YouTube player clients to find one that works.
    """
    global _COOKIES_ENABLED
    ram_path = ensure_ram_path(ram_disk_path)
    
    # We try these clients in order of guest-limit generosity
    clients = ["ios", "android", "web"]
    
    last_error = ""
    
    for client in clients:
        unique_id = str(uuid.uuid4())
        temp_template = str(ram_path / f"{unique_id}.%(ext)s")
        
        ydl_opts = {
            "format": "bestaudio/best", 
            "outtmpl": temp_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "noprogress": True,
            "js_runtime": "node",
            "extractor_args": {
                "youtube": {
                    "player_client": [client],
                    "skip": ["dash", "hls"]
                }
            },
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
            "postprocessor_args": ["-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le"],
        }

        # Check cookies
        current_cookies = cookies_path if (_COOKIES_ENABLED and cookies_path and os.path.exists(cookies_path)) else None
        if current_cookies:
            ydl_opts["cookiefile"] = current_cookies

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filepath = str(ram_path / f"{unique_id}.wav")
                return "SUCCESS", filepath, _parse_meta(info, url)
        except Exception as e:
            err_str = str(e).lower()
            last_error = err_str
            
            # If it is a bot challenge, we stop immediately to let main.py handle hibernate
            if "confirm you’re not a bot" in err_str or "429" in err_str:
                return "BOT_CHALLENGE", None, None
            
            # If it was a cookie error, disable them for the next client/run
            if "cookie" in err_str and _COOKIES_ENABLED:
                _COOKIES_ENABLED = False
                logger.warning(f"Cookies failed for client {client}. Disabling for this session.")
            
            # Otherwise, just try the next client
            continue

    logger.warning(f"All clients failed for {url}. Last error: {last_error}")
    return "ERROR", None, None

def _parse_meta(info: dict, original_url: str) -> dict:
    return {
        "id": info.get("id"),
        "title": info.get("title", "Unknown Title"),
        "url": info.get("webpage_url") or original_url,
        "uploader": info.get("uploader"),
        "channel": info.get("channel"),
        "upload_date": info.get("upload_date"),
        "view_count": info.get("view_count", 0),
        "like_count": info.get("like_count", 0),
        "duration": info.get("duration"),
        "categories": info.get("categories", []),
        "tags": info.get("tags", []),
    }
