from __future__ import annotations

import random
from typing import List

from .schemas import MapPoint, SearchResultItem


def _seed_for_query(query: str) -> int:
    if not query:
        return 37
    return max(17, sum(ord(char) for char in query) % 97)


def build_traditional_results(query: str, limit: int) -> List[SearchResultItem]:
    seed = _seed_for_query(query)
    items: List[SearchResultItem] = []

    for index in range(limit):
        score = max(0.25, 0.96 - (index * 0.08))
        base = seed + index
        items.append(
            SearchResultItem(
                id=f"trad-{base}",
                title=f"Cançó tradicional {index + 1}",
                artist=f"Grup {((base % 9) + 1)}",
                album=f"Àlbum demo {((base % 6) + 1)}",
                year=2000 + (base % 24),
                score=round(score, 2),
                preview=f"Coincidència parcial per a '{query or 'demo'}'",
            )
        )

    return items


def build_intelligent_results(query: str, limit: int) -> List[SearchResultItem]:
    seed = _seed_for_query(query) + 11
    items: List[SearchResultItem] = []

    for index in range(limit):
        score = max(0.20, 0.91 - (index * 0.07))
        base = seed + index
        items.append(
            SearchResultItem(
                id=f"smart-{base}",
                title=f"Cançó intel·ligent {index + 1}",
                artist=f"Artista {((base % 10) + 1)}",
                album=f"Col·lecció semàntica {((base % 5) + 1)}",
                year=1998 + (base % 27),
                score=round(score, 2),
                preview=f"Relació semàntica amb '{query or 'explora música catalana'}'",
            )
        )

    return items


def build_map_points(traditional: List[SearchResultItem], intelligent: List[SearchResultItem]) -> List[MapPoint]:
    points: List[MapPoint] = []
    merged = traditional[:4] + intelligent[:4]
    seed_input = "|".join(item.id for item in merged)
    seed = sum(ord(char) for char in seed_input) or 97
    rng = random.Random(seed)
    min_distance = 12.0

    def is_far_enough(x: float, y: float) -> bool:
        for existing in points:
            dx = existing.x - x
            dy = existing.y - y
            if (dx * dx + dy * dy) ** 0.5 < min_distance:
                return False
        return True

    for index, item in enumerate(merged):
        x = 50.0
        y = 50.0

        for _ in range(25):
            candidate_x = rng.uniform(8.0, 92.0)
            candidate_y = rng.uniform(8.0, 92.0)
            if is_far_enough(candidate_x, candidate_y):
                x = candidate_x
                y = candidate_y
                break

        if x == 50.0 and y == 50.0:
            x = 10.0 + (index * 9.0) % 80.0
            y = 12.0 + (index * 11.0) % 76.0

        points.append(
            MapPoint(
                song_id=item.id,
                label=item.title,
                x=round(x, 2),
                y=round(y, 2),
                cluster="Tradicional" if item.id.startswith("trad-") else "Intel·ligent",
            )
        )

    return points
