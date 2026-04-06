"""
FastAPI application entry point.

Run with:
    uvicorn app.backend.api.main:app --reload --host 127.0.0.1 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.api.routes.search import router as search_router

app = FastAPI(
    title="Semantic Song Search Engine",
    description="API for searching Catalan songs using semantic embeddings.",
    version="0.2.0",
)

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
    return {"status": "ok", "message": "Semantic Song Search Engine API v0.2"}
