from __future__ import annotations

import os
import tempfile
import logging
import uuid
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
) -> tuple[bool, str | None, dict | None]:
    """
    Peak-Resiliency Downloader with iOS/Android client bypass.
    """
    global _COOKIES_ENABLED
    ram_path = ensure_ram_path(ram_disk_path)
    unique_id = str(uuid.uuid4())
    temp_template = str(ram_path / f"{unique_id}.%(ext)s")

    base_opts = {
        "format": "bestaudio/best", 
        "outtmpl": temp_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "external_downloader": "aria2c",
        "external_downloader_args": ["-x", "16", "-s", "16", "-k", "1M"],
        "js_runtime": "node",
        # BYPASS: Tell YouTube we are an iPhone/Android app to get higher limits
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "web"],
                "skip": ["dash", "hls"]
            }
        },
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "postprocessor_args": ["-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le"],
    }

    # Attempt 1: With Cookies (if provided and enabled)
    if cookies_path and os.path.exists(cookies_path) and _COOKIES_ENABLED:
        opts_with_cookies = base_opts.copy()
        opts_with_cookies["cookiefile"] = cookies_path
        try:
            with yt_dlp.YoutubeDL(opts_with_cookies) as ydl:
                info = ydl.extract_info(url, download=True)
                return True, str(ram_path / f"{unique_id}.wav"), _parse_meta(info, url)
        except Exception as e:
            _COOKIES_ENABLED = False
            logger.warning(f"Cookies failed. Switching to High-Limit Mobile client. Error: {e}")

    # Attempt 2: Naked Mobile Download (The "Safe" Fallback)
    try:
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return True, str(ram_path / f"{unique_id}.wav"), _parse_meta(info, url)
    except Exception as e:
        logger.error(f"Download failed critically for {url}: {e}")
        return False, None, None

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
