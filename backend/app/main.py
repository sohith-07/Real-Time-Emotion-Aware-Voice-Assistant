"""FastAPI application entry point.

Wires up:
  * CORS for the frontend
  * SQLite database (auto-created on startup)
  * All API routers (chat, emotion, conversations, analytics, settings, voice)
  * Static serving of the frontend HTML/CSS/JS so the whole app runs from one
    server on http://localhost:8000
  * /health and / endpoints
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .models import seed_defaults
from .routers import (
    analytics,
    chat,
    conversations,
    emotion,
    settings as settings_router,
    voice,
)
from .services import emotion_service, llm_service

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Resolve the frontend directory (sibling of backend/).
BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    init_db()
    # Seed default settings if needed.
    from .database import db_session

    with db_session() as db:
        seed_defaults(db)
    logger.info("Startup complete. Emotion engine=%s, chat engine=%s",
                emotion_service.engine_status(), llm_service.active_engine())
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "Real-time voice assistant with emotion-aware dialogue. Detects "
        "emotion from speech text, adapts replies to the user's mood, and "
        "speaks responses via the Web Speech API."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# --- Health & root ---
@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "app_name": settings.app_name,
        "emotion_engine": emotion_service.engine_status(),
        "chat_engine": llm_service.active_engine(),
        "openai_configured": bool(settings.openai_api_key),
        "frontend_dir_exists": FRONTEND_DIR.exists(),
    }


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect to the landing page."""
    if (FRONTEND_DIR / "index.html").exists():
        return RedirectResponse(url="/index.html")
    return JSONResponse(
        {"message": "Backend is running. Frontend directory not found.",
         "frontend_dir": str(FRONTEND_DIR)},
        status_code=200,
    )


# --- API routers ---
app.include_router(chat.router)
app.include_router(emotion.router)
app.include_router(conversations.router)
app.include_router(analytics.router)
app.include_router(settings_router.router)
app.include_router(voice.router)


# --- Static frontend (mounted AFTER routers so /api/* takes precedence) ---
if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )

    # Friendly per-page routes: /voice -> voice.html, etc.
    @app.get("/{page}.html", include_in_schema=False)
    def page_html(page: str) -> FileResponse:
        path = FRONTEND_DIR / f"{page}.html"
        if not path.exists():
            return FileResponse(FRONTEND_DIR / "index.html")
        return FileResponse(path)

    # Bare routes like /voice, /chat, /analytics, /settings.
    @app.get("/{page}", include_in_schema=False)
    def bare_page(page: str) -> FileResponse:
        if page in ("voice", "chat", "analytics", "settings", "about"):
            return FileResponse(FRONTEND_DIR / f"{page}.html")
        # Fall back to landing for the root.
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    logger.warning("Frontend directory not found at %s", FRONTEND_DIR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )
