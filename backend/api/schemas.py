from typing import List

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    id: str
    title: str
    artist: str
    album: str
    year: int
    score: float = Field(ge=0.0, le=1.0)
    preview: str


class MapPoint(BaseModel):
    song_id: str
    label: str
    x: float = Field(ge=0.0, le=100.0)
    y: float = Field(ge=0.0, le=100.0)
    cluster: str


class SearchResponse(BaseModel):
    query: str
    traditional_results: List[SearchResultItem]
    intelligent_results: List[SearchResultItem]
    map_points: List[MapPoint]
