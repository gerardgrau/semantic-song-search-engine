"""
Embedding and similarity module.

MOCK: Uses simple substring matching to simulate semantic search.
REAL: Would use a multilingual sentence transformer (e.g., multilingual-e5-large)
      to encode queries and compute cosine similarity against pre-computed song embeddings.
"""

import random


def text_to_embedding(text: str) -> list[float]:
    """
    Convert a user query text into an embedding vector.

    MOCK: Returns a random vector of dimension 128.
    REAL: Would use multilingual-e5-large or similar model to encode the text.
          The model should be loaded once at startup and reused for all queries.
          For E5 models, prepend "query: " to the input text before encoding.

    Args:
        text: The user's search query string.

    Returns:
        A list of floats representing the query embedding (dimension depends on model).
    """
    return [random.uniform(-1.0, 1.0) for _ in range(128)]


def compute_similarity(query_embedding: list[float], song_embedding: list[float]) -> float:
    """
    Compute similarity between a query embedding and a song embedding.

    MOCK: Returns a random score between 0 and 1.
    REAL: Would compute cosine similarity between the two vectors:
          cos_sim = dot(a, b) / (norm(a) * norm(b))
          Could also use FAISS or similar library for efficient batch similarity.

    Args:
        query_embedding: The embedding vector for the user's query.
        song_embedding: The embedding vector for a song.

    Returns:
        A float between 0 and 1 representing similarity (1 = most similar).
    """
    return random.uniform(0.0, 1.0)


def filter_embeddings(query_text: str, songs: list[dict], top_k: int = 10) -> list[dict]:
    """
    Main filtering function. Takes a query text and all songs, returns songs
    scored by relevance to the query.

    MOCK: Performs case-insensitive substring matching on title, artist, and
          lyrics_snippet. Matching songs get a high score (0.7-1.0), while
          non-matching songs get a low score (0.1-0.5). This makes the mock
          testable and somewhat useful for development.
    REAL: Would:
          1. Encode the query text using text_to_embedding().
          2. Compute cosine similarity between the query embedding and every
             song's pre-computed embedding vector.
          3. Sort by similarity score descending.
          4. Optionally use approximate nearest neighbor search (FAISS, Annoy)
             for efficiency at scale (126k+ songs).

    Each returned song dict gets an added 'score' field (float 0-1).

    Args:
        query_text: The user's search query.
        songs: List of all song dicts (with metadata and embeddings).
        top_k: How many top results to highlight (used by frontend for styling).

    Returns:
        List of all songs with 'score' field added, sorted by score descending.
    """
    query_lower = query_text.lower().strip()
    scored_songs = []

    for song in songs:
        # Check for substring match in key text fields
        searchable_fields = [
            song.get("title", ""),
            song.get("artist", ""),
            song.get("lyrics_snippet", ""),
            song.get("album", ""),
            song.get("genre", ""),
        ]
        searchable_text = " ".join(searchable_fields).lower()

        if query_lower in searchable_text:
            # Match found: assign high score with some randomness for ranking variety
            score = round(random.uniform(0.7, 1.0), 4)
        else:
            # No match: assign low score
            score = round(random.uniform(0.1, 0.5), 4)

        scored_song = {**song, "score": score}
        scored_songs.append(scored_song)

    # Sort by score descending
    scored_songs.sort(key=lambda s: s["score"], reverse=True)

    return scored_songs
