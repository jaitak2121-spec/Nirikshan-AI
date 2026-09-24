"""
NIRIKSHAN AI — MPLADS Risk Intelligence & Investigation Network.

FastAPI application entry point.

Scope note
----------
This is a decision-support prototype running on synthetic data. It surfaces
risk signals and the evidence behind them; it does not establish wrongdoing and
does not make decisions. Every determination remains with the authorised
officer reviewing the record.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from anomaly_engine.explanation_engine import DISCLAIMER

from .database import DB_PATH, SessionLocal, init_db
from .routers import analysis, cases, dashboard, intelligence, projects
from .schemas import HealthResponse
from .services.analysis_service import DATA_NOTICE

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("nirikshan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed on first start so a demo never opens onto an empty dashboard and no
    # manual database step is needed.
    result = init_db()
    if result.get("seeded"):
        log.info(
            "Seeded synthetic dataset: %s projects, %s payments -> %s",
            result.get("projects"), result.get("payments"), result.get("database"),
        )
    else:
        log.info("Database already populated: %s projects", result.get("projects"))
    yield


app = FastAPI(
    title="NIRIKSHAN AI",
    description=(
        "MPLADS Risk Intelligence & Investigation Network — prototype. "
        "Operates on synthetic demonstration data only."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# The frontend dev server proxies /api, but permissive CORS keeps the prototype
# working if it is opened from a different port or origin during a demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(dashboard.router)
app.include_router(analysis.router)
app.include_router(cases.router)
# Registered after the others because it claims /api/agencies/{agency}, which
# must not shadow the /api/agencies list above it.
app.include_router(intelligence.router)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    """Return a readable error instead of dropping the connection.

    The frontend can then show a real message rather than a blank screen, which
    matters more in a live demo than a stack trace does.
    """
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "The analysis service encountered an internal error.",
            "path": request.url.path,
            "error_type": type(exc).__name__,
        },
    )


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health():
    """Liveness plus enough context for the UI to explain an outage."""
    from .models import Project

    with SessionLocal() as db:
        count = db.query(Project).count()

    return {
        "status": "ok",
        "database": str(DB_PATH),
        "projects_in_database": count,
        "engine": "NIRIKSHAN anomaly engine v0.1 (deterministic, rule-based)",
        "data_notice": DATA_NOTICE,
    }


@app.get("/api", tags=["system"])
def api_root():
    return {
        "name": "NIRIKSHAN AI",
        "subtitle": "MPLADS Risk Intelligence & Investigation Network",
        "version": "0.1.0",
        "data_notice": DATA_NOTICE,
        "disclaimer": DISCLAIMER,
        "endpoints": [
            "GET  /api/health",
            "GET  /api/projects",
            "GET  /api/projects/{project_id}",
            "GET  /api/projects/{project_id}/similar",
            "GET  /api/projects/{project_id}/nearby",
            "POST /api/projects/{project_id}/analyze",
            "GET  /api/projects/{project_id}/anomalies",
            "GET  /api/dashboard/stats",
            "GET  /api/investigation-queue",
            "GET  /api/agencies",
            "GET  /api/agencies/{agency}",
            "GET  /api/methodology",
            "GET  /api/roles",
            "GET  /api/me",
            "GET  /api/cases",
            "POST /api/cases",
            "GET  /api/cases/{case_id}",
            "POST /api/cases/{case_id}/assign",
            "POST /api/cases/{case_id}/status",
            "POST /api/cases/{case_id}/outcome",
            "POST /api/cases/{case_id}/remarks",
            "PATCH /api/cases/{case_id}/checklist/{item_key}",
            "GET  /api/audit",
            "GET  /api/compliance",
            "GET  /api/trends",
            "GET  /api/watchlist",
            "GET  /api/projects/{project_id}/network",
            "GET  /api/projects/{project_id}/what-if",
        ],
        "identity": (
            "Send the X-Nirikshan-User header to act as a demonstration role. "
            "Without it the API answers with the national (ministry) view."
        ),
    }


# --------------------------------------------------------------------------
# Built frontend
# --------------------------------------------------------------------------
# If frontend/dist exists, the API also serves the React app. That means one
# process serves the whole prototype: `uvicorn backend.main:app` on its own is
# enough for a demo, and the deployed function does not depend on the host's
# static-file routing being configured correctly.
#
# Registered last so every /api route above takes precedence.

_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if (_DIST / "index.html").is_file():
    if (_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        """Serve index.html for any non-API path so client-side routing works.

        A deep link such as /project/MPLAD-2026-024 is a real URL to React
        Router but not a file on disk, so it has to fall back to the shell.
        """
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = (_DIST / full_path).resolve() if full_path else None
        if candidate and candidate.is_file() and candidate.is_relative_to(_DIST):
            return FileResponse(candidate)

        return FileResponse(_DIST / "index.html")

else:  # pragma: no cover - depends on whether the frontend has been built
    log.warning(
        "frontend/dist not found — serving the API only. "
        "Run `npm run build` in frontend/ to have the UI served from here too."
    )
