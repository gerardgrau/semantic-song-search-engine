"""Pydantic models for API request/response validation."""

from pydantic import BaseModel


class SongResult(BaseModel):
    """A song with its search relevance score."""

    id: int
    title: str
    artist: str
    album: str
    genre: str
    year: int
    lyrics_snippet: str
    score: float = 0.0


class Point2D(BaseModel):
    """A 2D projection point for the song map."""

    id: int
    x: float
    y: float
    title: str
    artist: str
    genre: str


class Point3D(BaseModel):
    """A 3D projection point for the song map."""

    id: int
    x: float
    y: float
    z: float
    title: str
    artist: str
    genre: str


class SearchResponse(BaseModel):
    """Response for a search query."""

    query: str
    songs: list[SongResult]
    points_2d: list[Point2D]
    points_3d: list[Point3D]
    total_filtered: int
    message: str | None = None


class AllSongsResponse(BaseModel):
    """Response for loading all songs (initial load / reset)."""

    songs: list[SongResult]
    points_2d: list[Point2D]
    points_3d: list[Point3D]
    total: int
