from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.search import router as search_router

app = FastAPI(
    title="Semantic Song Search API (Prototype)",
    version="0.1.0",
    description=(
        "Mock backend for frontend layout demos. "
        "Real traditional and intelligent engines will be integrated later."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "semantic-song-search-prototype",
        "status": "ok",
        "message": "Mock API ready",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
