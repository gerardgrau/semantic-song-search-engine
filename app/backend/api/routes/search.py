"""API routes for song search and retrieval."""

from fastapi import APIRouter, HTTPException, Query

from app.backend.api.schemas import (
    AllSongsResponse,
    Point2D,
    Point3D,
    SearchResponse,
    SongResult,
)
from app.backend.core.data_loader import get_song_by_id, load_all_songs
from app.backend.core.embeddings import filter_embeddings
from app.backend.core.projections import get_projections_2d, get_projections_3d

router = APIRouter(prefix="/api")


def _song_to_result(song: dict, default_score: float = 0.0) -> SongResult:
    """Convert a raw song dict to a SongResult schema."""
    return SongResult(
        id=song["id"],
        title=song["title"],
        artist=song["artist"],
        album=song["album"],
        genre=song["genre"],
        year=song["year"],
        lyrics_snippet=song["lyrics_snippet"],
        score=song.get("score", default_score),
    )


@router.get("/songs", response_model=AllSongsResponse)
def get_all_songs():
    """
    Returns all songs with their 2D and 3D projections.

    Used for the initial page load and when the user resets the search.
    """
    songs = load_all_songs()
    song_results = [_song_to_result(s) for s in songs]
    points_2d = [Point2D(**p) for p in get_projections_2d()]
    points_3d = [Point3D(**p) for p in get_projections_3d()]

    return AllSongsResponse(
        songs=song_results,
        points_2d=points_2d,
        points_3d=points_3d,
        total=len(songs),
    )


@router.get("/search", response_model=SearchResponse)
def search_songs(q: str = Query(..., min_length=1, description="Search query text")):
    """
    Filter songs by semantic similarity to the query text.

    Returns all songs scored by relevance, along with 2D/3D projections
    for the map visualization.
    """
    all_songs = load_all_songs()
    scored_songs = filter_embeddings(query_text=q, songs=all_songs)

    song_results = [_song_to_result(s) for s in scored_songs]

    # Count how many songs have a "high" relevance score (mock threshold)
    high_score_threshold = 0.7
    total_filtered = sum(1 for s in scored_songs if s["score"] >= high_score_threshold)

    # Get projections for all songs (frontend decides which to highlight)
    points_2d = [Point2D(**p) for p in get_projections_2d()]
    points_3d = [Point3D(**p) for p in get_projections_3d()]

    message = None
    if total_filtered == 0:
        message = f"No s'han trobat resultats rellevants per a '{q}'. Mostrant totes les cançons ordenades per rellevància."
    elif total_filtered < 10:
        message = f"S'han trobat {total_filtered} cançons rellevants per a '{q}'."

    return SearchResponse(
        query=q,
        songs=song_results,
        points_2d=points_2d,
        points_3d=points_3d,
        total_filtered=total_filtered,
        message=message,
    )


@router.get("/songs/{song_id}", response_model=SongResult)
def get_song(song_id: int):
    """Get a single song by its ID."""
    song = get_song_by_id(song_id)
    if song is None:
        raise HTTPException(status_code=404, detail=f"Song with id {song_id} not found")
    return _song_to_result(song)
