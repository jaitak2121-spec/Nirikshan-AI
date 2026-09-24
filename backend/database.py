"""SQLite engine, session factory and first-run initialisation."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# The database file lives in the top-level `database/` directory so that the
# storage layer is visibly separate from the API layer.
BASE_DIR = Path(__file__).resolve().parent.parent

# On a serverless host the project directory is read-only and only /tmp can be
# written, so the database is placed there instead. It is re-created and
# re-seeded on a cold start, which is cheap (26 records) and keeps the deployed
# demo self-contained without an external database.
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DB_DIR = Path("/tmp/nirikshan")
else:
    DB_DIR = BASE_DIR / "database"

DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "nirikshan.db"

DATABASE_URL = os.environ.get("NIRIKSHAN_DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(force_reseed: bool = False) -> dict:
    """Create tables and seed synthetic data if the database is empty.

    Called on application startup so the dashboard is never empty during a
    demo and no manual database step is required.
    """
    from . import models  # noqa: F401  (registers mappers)
    from .data.seed_data import seed

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing = db.query(models.Project).count()
        if existing and not force_reseed:
            return {"seeded": False, "projects": existing, "database": str(DB_PATH)}

        if force_reseed:
            db.query(models.Payment).delete()
            db.query(models.Project).delete()
            db.commit()

        counts = seed(db)
        return {"seeded": True, "database": str(DB_PATH), **counts}
