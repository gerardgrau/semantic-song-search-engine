"""
Projection module for 2D and 3D song map coordinates.

MOCK: Returns pre-computed embedding_2d / embedding_3d values from mock data.
REAL: Would compute or retrieve UMAP/t-SNE projections from the full
      high-dimensional embedding space. Projections would typically be
      pre-computed in batch and stored alongside the song data, then
      re-computed when the embedding model or song corpus changes.
"""

from app.backend.core.data_loader import load_all_songs


def get_projections_2d(song_ids: list[int] | None = None) -> list[dict]:
    """
    Get 2D projections for songs.

    MOCK: Returns the pre-computed embedding_2d from mock data.
    REAL: Would return UMAP/t-SNE 2D projections from the full embedding space.
          These projections reduce high-dimensional embeddings (e.g., 768-dim)
          to 2D coordinates for visualization. Typically pre-computed with:
            - UMAP(n_components=2, metric='cosine', n_neighbors=15)
            - or t-SNE(n_components=2, perplexity=30)

    Args:
        song_ids: Optional list of song IDs to filter. If None, returns all.

    Returns:
        List of dicts with {id, x, y, title, artist, genre}.
    """
    songs = load_all_songs()

    if song_ids is not None:
        id_set = set(song_ids)
        songs = [s for s in songs if s["id"] in id_set]

    return [
        {
            "id": song["id"],
            "x": song["embedding_2d"][0],
            "y": song["embedding_2d"][1],
            "title": song["title"],
            "artist": song["artist"],
            "genre": song["genre"],
        }
        for song in songs
    ]


def get_projections_3d(song_ids: list[int] | None = None) -> list[dict]:
    """
    Get 3D projections for songs.

    MOCK: Returns the pre-computed embedding_3d from mock data.
    REAL: Would return UMAP/t-SNE 3D projections from the full embedding space.
          Same as 2D but with n_components=3 for 3D visualization.

    Args:
        song_ids: Optional list of song IDs to filter. If None, returns all.

    Returns:
        List of dicts with {id, x, y, z, title, artist, genre}.
    """
    songs = load_all_songs()

    if song_ids is not None:
        id_set = set(song_ids)
        songs = [s for s in songs if s["id"] in id_set]

    return [
        {
            "id": song["id"],
            "x": song["embedding_3d"][0],
            "y": song["embedding_3d"][1],
            "z": song["embedding_3d"][2],
            "title": song["title"],
            "artist": song["artist"],
            "genre": song["genre"],
        }
        for song in songs
    ]
