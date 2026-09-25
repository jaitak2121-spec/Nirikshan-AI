"""Vercel Python serverless entry point.

Vercel's Python runtime imports this module and serves the ASGI ``app`` it
exposes. Seeding is done here at import time rather than relying on FastAPI's
lifespan hook, which is not guaranteed to run under the serverless wrapper — a
cold start must never serve an empty dashboard.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# The function bundle is rooted at api/, so the repository root has to be on the
# path for `backend` and `anomaly_engine` to be importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db  # noqa: E402
from backend.main import app  # noqa: E402

try:
    init_db()
except Exception:
    # Never let seeding abort the import. An exception here would take the
    # whole function down with an opaque FUNCTION_INVOCATION_FAILED on every
    # route; logging it instead keeps the app serving and puts the real
    # traceback in the deployment logs where it can be read.
    logging.getLogger("nirikshan.vercel").exception(
        "Cold-start seeding failed — the API will report errors until this is "
        "resolved."
    )

__all__ = ["app"]
