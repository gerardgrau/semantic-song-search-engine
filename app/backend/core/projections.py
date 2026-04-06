"""
Projection module — computes t-SNE 2D and 3D from k-dimensional embeddings.

The full-dataset projections are cached so that a "reset" is instant.
Any filtered subset triggers a fresh t-SNE computation.
"""

from __future__ import annotations

import numpy as np
from sklearn.manifold import TSNE

from app.backend.core.data_loader import load_all_songs

# ---------------------------------------------------------------------------
# Cache for full-dataset projections (computed once, reused on reset)
# ---------------------------------------------------------------------------
_cached_all_2d: list[dict] | None = None
_cached_all_3d: list[dict] | None = None


def _songs_to_matrix(songs: list[dict]) -> np.ndarray:
    """Extract the k-dim embedding from each song into an (n, k) numpy array."""
    return np.array([s["embedding"] for s in songs], dtype=np.float64)


def _run_tsne(matrix: np.ndarray, n_components: int) -> np.ndarray:
    """
    Run t-SNE on an (n, k) matrix and return (n, n_components) coordinates.

    Handles edge cases:
      - n == 1  → return origin
      - n < 4   → use PCA init and perplexity = max(1, n-1)
      - n >= 4  → standard t-SNE with perplexity = min(30, n-1)
    """
    n = matrix.shape[0]
    if n <= 1:
        return np.zeros((n, n_components))

    perplexity = min(30, n - 1)
    perplexity = max(1, perplexity)

    init = "pca" if n >= n_components else "random"

    tsne = TSNE(
        n_components=n_components,
        perplexity=perplexity,
        random_state=42,
        init=init,
        max_iter=500,
    )
    return tsne.fit_transform(matrix)


def _build_points(songs: list[dict], coords: np.ndarray, dims: int) -> list[dict]:
    """Combine song metadata with projected coordinates."""
    points = []
    for i, song in enumerate(songs):
        p = {
            "id": song["id"],
            "x": round(float(coords[i, 0]), 4),
            "y": round(float(coords[i, 1]), 4),
            "title": song["title"],
            "artist": song["artist"],
            "genre": song["genre"],
        }
        if dims == 3:
            p["z"] = round(float(coords[i, 2]), 4)
        points.append(p)
    return points


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_tsne_2d(songs: list[dict]) -> list[dict]:
    """
    Compute t-SNE 2D projections from the k-dimensional 'embedding' field.

    Args:
        songs: list of song dicts, each must contain 'embedding' (list[float]).

    Returns:
        List of {id, x, y, title, artist, genre}.
    """
    if not songs:
        return []
    matrix = _songs_to_matrix(songs)
    coords = _run_tsne(matrix, n_components=2)
    return _build_points(songs, coords, dims=2)


def compute_tsne_3d(songs: list[dict]) -> list[dict]:
    """
    Compute t-SNE 3D projections from the k-dimensional 'embedding' field.

    Args:
        songs: list of song dicts, each must contain 'embedding' (list[float]).

    Returns:
        List of {id, x, y, z, title, artist, genre}.
    """
    if not songs:
        return []
    matrix = _songs_to_matrix(songs)
    coords = _run_tsne(matrix, n_components=3)
    return _build_points(songs, coords, dims=3)


def get_all_projections_2d() -> list[dict]:
    """
    Get cached 2D projections for ALL songs.
    Computes t-SNE on first call, then returns the cache.
    """
    global _cached_all_2d
    if _cached_all_2d is None:
        _cached_all_2d = compute_tsne_2d(load_all_songs())
    return _cached_all_2d


def get_all_projections_3d() -> list[dict]:
    """
    Get cached 3D projections for ALL songs.
    Computes t-SNE on first call, then returns the cache.
    """
    global _cached_all_3d
    if _cached_all_3d is None:
        _cached_all_3d = compute_tsne_3d(load_all_songs())
    return _cached_all_3d


def invalidate_cache() -> None:
    """Clear projection caches (e.g. if the song corpus changes)."""
    global _cached_all_2d, _cached_all_3d
    _cached_all_2d = None
    _cached_all_3d = None
