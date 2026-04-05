"""
FastAPI application entry point.

Run with:
    uvicorn app.backend.api.main:app --reload
    (from the project root: /mnt/c/Users/eloip/Documents/UPC/PE/semantic-song-search-engine)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.api.routes.search import router as search_router

app = FastAPI(
    title="Semantic Song Search Engine",
    description="API for searching Catalan songs using semantic embeddings and visualizing them on a 2D/3D map.",
    version="0.1.0",
)

# CORS: allow all origins for local development.
# REAL: Restrict origins to the frontend domain in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)


@app.get("/")
def root():
    """Health check / landing endpoint."""
    return {"status": "ok", "message": "Semantic Song Search Engine API"}
