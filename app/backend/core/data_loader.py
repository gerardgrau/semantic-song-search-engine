"""
Data loading module.

MOCK: Loads songs from a local JSON file (mock_songs.json).
REAL: Would connect to a database (PostgreSQL, Elasticsearch, etc.)
      and query songs with their metadata and embeddings.
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent / "data" / "mock_songs.json"

# In-memory cache to avoid re-reading the file on every request
_songs_cache: list[dict] | None = None


def load_all_songs() -> list[dict]:
    """
    Load all songs from storage. Returns list of song dicts with all metadata.

    MOCK: Reads from data/mock_songs.json and caches in memory.
    REAL: Would query a database (e.g., PostgreSQL with pgvector) to fetch
          all songs with their metadata, lyrics snippets, and embedding vectors.
          Should support pagination for large datasets (126k+ songs).

    Returns:
        List of song dicts, each containing: id, title, artist, album, genre,
        year, lyrics_snippet, embedding_2d, embedding_3d.
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

    Args:
        song_id: The integer ID of the song to retrieve.

    Returns:
        The song dict if found, or None if no song has that ID.
    """
    songs = load_all_songs()
    for song in songs:
        if song["id"] == song_id:
            return song
    return None
