"""
SAHAYA — FastAPI application entry point.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load configuration before importing routers. The extractor singleton is
# created during router import and needs OPENAI_API_KEY at construction time.
load_dotenv()

from app.api.incidents import router as incidents_router
from app.api.resources import router as resources_router
from app.api.evaluations import router as evaluations_router
from app.api.audio import router as audio_router
from app.api.people import group_router, router as people_router
from app.api.routes import router as routes_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — seed data is loaded at import time in memory.py
    print("SAHAYA backend starting up...")
    print(f"  OpenAI model: {os.getenv('OPENAI_MODEL', 'gpt-4o')}")
    print(f"  OpenAI key set: {'YES' if os.getenv('OPENAI_API_KEY') else 'NO — AI features degraded'}")
    yield
    print("SAHAYA backend shutting down.")


app = FastAPI(
    title="SAHAYA API",
    description=(
        "Inclusive Emergency Decision Engine. "
        "AI understands. Rules verify. Humans decide."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow frontend origin
# ---------------------------------------------------------------------------

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(incidents_router)
app.include_router(resources_router)
app.include_router(evaluations_router)
app.include_router(audio_router)
app.include_router(people_router)
app.include_router(group_router)
app.include_router(routes_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "service": "SAHAYA API",
        "ai_available": bool(os.getenv("OPENAI_API_KEY")),
        "version": "1.0.0",
    }


@app.get("/", tags=["health"])
async def root():
    return {"message": "SAHAYA API — Inclusive Emergency Decision Engine"}
