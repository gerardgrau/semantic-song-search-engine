"""
Data loading module.

MOCK: Loads songs from a local JSON file (mock_songs.json).
REAL: Would connect to a database (PostgreSQL, Elasticsearch, etc.)
      and query songs with their metadata and embeddings.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent / "data" / "mock_songs.json"

_songs_cache: list[dict] | None = None


def load_all_songs() -> list[dict]:
    """
    Load all songs from storage.

    MOCK: Reads from data/mock_songs.json and caches in memory.
    REAL: Would query a database to fetch all songs with metadata and embeddings.

    Returns:
        List of song dicts with: id, title, artist, album, genre, year,
        lyrics_snippet, full_lyrics, url, duration, language, embedding.
    """
    global _songs_cache
    if _songs_cache is None:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            _songs_cache = json.load(f)
    return _songs_cache


def get_song_by_id(song_id: int) -> dict | None:
    """
    Get a single song by its ID.

    MOCK: Linear scan through the cached song list.
    REAL: Would perform an indexed database lookup by primary key.
    """
    for song in load_all_songs():
        if song["id"] == song_id:
            return song
    return None


def get_songs_by_ids(song_ids: list[int]) -> list[dict]:
    """
    Get multiple songs by their IDs, preserving the order of song_ids.

    MOCK: Filters the cached list.
    REAL: Would do a batch query (WHERE id IN (...)).
    """
    id_set = set(song_ids)
    id_to_song = {s["id"]: s for s in load_all_songs() if s["id"] in id_set}
    return [id_to_song[sid] for sid in song_ids if sid in id_to_song]
