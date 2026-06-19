"""Job-Market Intelligence API — the monetizable B2B data feed.

Serves the gold marts produced by the Spark pipeline. Interactive docs at /docs.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import query
from .routers import salary, skills
from .schemas import Kpi

app = FastAPI(
    title="Job-Market Intelligence API",
    description="Real-time, skill-level, Taiwan-local job-market demand & salary data.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(skills.router)
app.include_router(salary.router)


@app.get("/health", tags=["meta"])
def health():
    try:
        query("SELECT 1")
        return {"status": "ok", "db": "up"}
    except Exception as e:  # noqa: BLE001
        return {"status": "degraded", "db": "down", "error": str(e)}


@app.get("/summary", response_model=list[Kpi], tags=["meta"])
def summary():
    return query("SELECT metric, value FROM market_kpi ORDER BY metric")


@app.get("/", tags=["meta"])
def root():
    return {
        "service": "Job-Market Intelligence API",
        "docs": "/docs",
        "endpoints": [
            "/skills", "/skills/trending", "/skills/{skill}/trend",
            "/salary", "/summary", "/health",
        ],
    }
