"""Vercel Python serverless entry point.

Vercel's Python runtime imports this module and serves the ASGI ``app`` it
exposes. Seeding is done here at import time rather than relying on FastAPI's
lifespan hook, which is not guaranteed to run under the serverless wrapper — a
cold start must never serve an empty dashboard.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The function bundle is rooted at api/, so the repository root has to be on the
# path for `backend` and `anomaly_engine` to be importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db  # noqa: E402
from backend.main import app  # noqa: E402

init_db()

__all__ = ["app"]
