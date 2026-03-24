from fastapi import APIRouter, Query

from ..mock_data import (
    build_intelligent_results,
    build_map_points,
    build_traditional_results,
)
from ..schemas import SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(default="", description="User query"),
    limit: int = Query(default=5, ge=1, le=20),
) -> SearchResponse:
    traditional = build_traditional_results(query=q.strip(), limit=limit)
    intelligent = build_intelligent_results(query=q.strip(), limit=limit)
    map_points = build_map_points(traditional=traditional, intelligent=intelligent)

    return SearchResponse(
        query=q,
        traditional_results=traditional,
        intelligent_results=intelligent,
        map_points=map_points,
    )
