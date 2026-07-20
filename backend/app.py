"""
app.py
NutriMama AI — main FastAPI application entry point.

Run locally:
    uvicorn app:app --reload

This wires up: CORS, centralized exception handling, DB initialization,
all routers, and (in Phase 4) static file serving for the Bootstrap frontend.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
import os

from config import settings
from database import init_db
from utils.logger import get_logger

from routes import auth, users, dashboard, mealplanner, nutrition, reminders, reports, ai_chat, foodsafety, upload, admin

logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description=(
        "Agentic AI Pregnancy Nutrition Assistant — FastAPI backend. "
        "Educational use only; not a substitute for professional medical advice."
    ),
    version="0.4.0-phase4",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Centralized exception handling ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request data", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# --- Startup ---
@app.on_event("startup")
def on_startup():
    init_db()
    logger.info(f"{settings.app_name} started in '{settings.app_env}' mode")

    # Auto-build the RAG index on first run if it's empty, so /chat and
    # /foodsafety/check have real retrieval available immediately without a
    # manual admin step. Safe to skip/fail — agents degrade gracefully if the
    # index stays empty (see rag/retriever.py).
    try:
        from rag.chromadb import index_stats, rebuild_index
        if index_stats()["chunks_indexed"] == 0:
            logger.info("RAG index is empty — building it from rag/documents/ now...")
            stats = rebuild_index()
            logger.info(f"RAG index build complete: {stats}")
    except Exception as exc:  # noqa: BLE001 — never block app startup on this
        logger.error(f"RAG index auto-build failed (non-fatal, app will still start): {exc}", exc_info=True)


# --- Routers ---
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(dashboard.router)
app.include_router(mealplanner.router)
app.include_router(nutrition.router)
app.include_router(reminders.router)
app.include_router(reports.router)
app.include_router(ai_chat.router)
app.include_router(foodsafety.router)
app.include_router(upload.router)
app.include_router(admin.router)


@app.get("/api/status", tags=["Health"])
def api_status():
    return {
        "app": settings.app_name,
        "status": "running",
        "phase": "4 of 5 — see README.md Build Status",
        "docs": "/docs",
        "disclaimer": (
            "This assistant provides educational information only and is not a substitute "
            "for professional medical advice. Always consult a qualified healthcare professional "
            "before making medical decisions."
        ),
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


# --- Serve the frontend (Phase 4) ---
# Mounted LAST and at "/" so it acts as a catch-all for anything not matched by
# an API route above (Starlette checks routes in registration order — specific
# API routes like /auth/login always win over this catch-all static mount).
# html=True lets each page be requested by its literal filename (e.g. /dashboard.html)
# and serves index.html for "/".
_frontend_dir = os.path.join(os.path.dirname(__file__), settings.frontend_dir)
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
    logger.info(f"Serving frontend from {_frontend_dir}")
else:
    logger.warning(f"Frontend directory not found at {_frontend_dir} — only the API will be served.")
