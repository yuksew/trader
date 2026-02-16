"""FastAPI application entry point for traders-tool."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import alerts, education, portfolio, review, risk, screening, signals, simulation
from src.api.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    # --- startup ---
    from src.api.database import init_db_async

    await init_db_async()
    start_scheduler()
    yield
    # --- shutdown ---
    stop_scheduler()


app = FastAPI(
    title="traders-tool API",
    description="ずぼら×低リスク 株式投資ツール",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - Streamlit (default port 8501) からのアクセスを許可
_default_origins = "http://localhost:8501,http://127.0.0.1:8501"
_cors_origins = [
    o.strip()
    for o in os.environ.get("TRADERS_CORS_ORIGINS", _default_origins).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Router registration ---
app.include_router(portfolio.router, prefix="/api", tags=["portfolio"])
app.include_router(screening.router, prefix="/api", tags=["screening"])
app.include_router(signals.router, prefix="/api", tags=["signals"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])
app.include_router(risk.router, prefix="/api", tags=["risk"])
app.include_router(education.router, prefix="/api", tags=["education"])
app.include_router(simulation.router, prefix="/api", tags=["simulation"])
app.include_router(review.router, prefix="/api", tags=["review"])


@app.get("/api/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
