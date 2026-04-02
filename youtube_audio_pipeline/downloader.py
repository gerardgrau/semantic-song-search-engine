from __future__ import annotations

import os
import tempfile
import logging
import subprocess
import numpy as np
from pathlib import Path

import yt_dlp

logger = logging.getLogger(__name__)

def download_to_memory(url: str) -> tuple[bool, np.ndarray | None, dict | None]:
    """
    EXPERIMENTAL: Streams audio directly from YouTube to a NumPy array via FFmpeg pipe.
    Bypasses disk I/O entirely.
    """
    # 1. Fetch metadata first (fast)
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get("url")
            metadata = {
                "id": info.get("id"),
                "title": info.get("title", "Unknown Title"),
                "url": url,
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
            }
    except Exception as e:
        return False, None, None

    # 2. Pipe Stream to FFmpeg
    # command: ffmpeg -i [url] -f s16le -acodec pcm_s16le -ar 16000 -ac 1 pipe:1
    cmd = [
        "ffmpeg", "-i", stream_url,
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        "-loglevel", "quiet", "pipe:1"
    ]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw_audio, _ = process.communicate()
        
        # Convert raw bytes to numpy array (float32 [-1, 1])
        audio_int16 = np.frombuffer(raw_audio, dtype=np.int16)
        audio_float = audio_int16.astype(np.float32) / 32768.0
        
        return True, audio_float, metadata
    except Exception as e:
        return False, None, None

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
) -> tuple[bool, str | None, dict | None]:
    """
    Standard production downloader (WAV on RAM Disk).
    """
    ram_path = ensure_ram_path(ram_disk_path)
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(ram_path / "%(id)s.%(ext)s"),
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "external_downloader": "aria2c",
        "external_downloader_args": ["-x", "16", "-s", "16", "-k", "1M"],
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav", "preferredquality": "192"}],
        "postprocessor_args": ["-ar", "16000", "-ac", "1"],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".wav"
            metadata = {
                "id": info.get("id"), "title": info.get("title", "Unknown Title"),
                "url": info.get("webpage_url") or url, "uploader": info.get("uploader"),
                "view_count": info.get("view_count", 0), "like_count": info.get("like_count", 0),
                "duration": info.get("duration"),
            }
            return True, filepath, metadata
    except Exception as e:
        logger.warning(f"Download failed for {url}: {e}")
        return False, None, None
