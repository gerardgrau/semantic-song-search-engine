"""
Embedding and similarity module — progressive filtering.

MOCK: Uses substring matching to simulate semantic search.
REAL: Would use a multilingual sentence transformer (e.g. multilingual-e5-large)
      to encode queries and compute cosine similarity against pre-computed song
      embeddings.
"""

from __future__ import annotations

import random


def text_to_embedding(text: str) -> list[float]:
    """
    Convert a user query text into an embedding vector.

    MOCK: Returns a deterministic-ish random vector of dimension 32 seeded
          by the hash of the text, so repeated queries give the same result.
    REAL: Would use multilingual-e5-large or similar model to encode the text.
          Prepend "query: " to the input for E5 models.

    Args:
        text: The user's search query string.
    Returns:
        A list of floats representing the query embedding.
    """
    rng = random.Random(hash(text))
    return [rng.uniform(-1.0, 1.0) for _ in range(32)]


def compute_similarity(query_embedding: list[float], song_embedding: list[float]) -> float:
    """
    Compute similarity between a query embedding and a song embedding.

    MOCK: Returns a random score.
    REAL: Would compute cosine similarity: dot(a,b) / (‖a‖·‖b‖).

    Returns:
        Float between 0 and 1 (1 = most similar).
    """
    return random.uniform(0.0, 1.0)


def filter_embeddings(query_text: str, songs: list[dict]) -> list[dict]:
    """
    Progressive filter.  Given a query and the CURRENT subset of songs
    (which may already have been narrowed by earlier queries), returns a
    further-filtered subset with relevance scores.

    The frontend tracks the surviving song IDs across queries.  Each call
    to this function narrows the set further.

    MOCK implementation
    -------------------
    1. Case-insensitive substring match on title / artist / lyrics / genre / album.
    2. Matching songs get a high score (0.70 – 1.00).
    3. Non-matching songs get a low score (0.05 – 0.40).
    4. All matches are kept.  ~30 % of non-matches are also kept (random)
       so that the set shrinks gradually.
    5. The function NEVER returns an empty list.  If everything would be
       removed, the single best-scoring song is retained.

    REAL implementation (to be replaced)
    ------------------------------------
    1. Encode query_text with text_to_embedding().
    2. Compute cosine similarity against each song's pre-computed embedding.
    3. Apply an adaptive threshold (e.g. percentile-based) to decide which
       songs survive.
    4. Return survivors sorted by score descending, minimum 1.

    Args:
        query_text: The user's search query.
        songs:      Current subset of songs (already filtered by previous queries).
    Returns:
        A filtered list of song dicts, each with an added 'score' field,
        sorted by score descending.  Always contains ≥ 1 song.
    """
    query_lower = query_text.lower().strip()
    if not query_lower:
        # Empty query → return everything with neutral score
        return [{**s, "score": 0.5} for s in songs]

    matches = []
    non_matches = []

    for song in songs:
        searchable = " ".join([
            song.get("title", ""),
            song.get("artist", ""),
            song.get("lyrics_snippet", ""),
            song.get("album", ""),
            song.get("genre", ""),
        ]).lower()

        if query_lower in searchable:
            score = round(random.uniform(0.70, 1.00), 4)
            matches.append({**song, "score": score})
        else:
            score = round(random.uniform(0.05, 0.40), 4)
            non_matches.append({**song, "score": score})

    # Keep all matches + a random ~30% of non-matches
    kept_non_matches = [s for s in non_matches if random.random() < 0.30]

    survivors = matches + kept_non_matches

    # Never return empty
    if not survivors:
        # Fall back: keep the single best non-match (or the first song)
        if non_matches:
            non_matches.sort(key=lambda s: s["score"], reverse=True)
            survivors = [non_matches[0]]
        else:
            survivors = [{**songs[0], "score": 0.10}]

    survivors.sort(key=lambda s: s["score"], reverse=True)
    return survivors
