"""
HTTP API: upload an audio file, follow its rendering and download the MP4.

Usage (from the repository root, with a single worker since the tasks live in memory):
    uvicorn src.api.main:app --reload
Interactive docs at http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI

from src.api.routes import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Sonic Brownian API", version="0.1.0")
    app.include_router(api_router)
    return app


app = create_app()
