"""SQLite engine, session factory and first-run initialisation."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

log = logging.getLogger("nirikshan.database")

# The database file lives in the top-level `database/` directory so that the
# storage layer is visibly separate from the API layer.
BASE_DIR = Path(__file__).resolve().parent.parent

_SQLITE_PREFIX = "sqlite:///"


def _is_writable(directory: Path) -> bool:
    """True if this process can create `directory` and write a file inside it."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".write-probe"
        probe.touch()
        probe.unlink()
    except OSError:
        return False
    return True


def _resolve_db_dir() -> Path:
    """Pick a directory this process can actually write to.

    A serverless host (Vercel) ships the project on a read-only filesystem and
    allows writes only under the system temp directory. Testing for a `VERCEL`
    environment variable is not reliable, because Vercel exposes that variable
    to the runtime only when "Enable access to System Environment Variables" is
    ticked on the project — so the filesystem is probed directly instead. Run
    locally, the project directory is writable and the path is unchanged.
    """
    preferred = BASE_DIR / "database"
    if _is_writable(preferred):
        return preferred

    fallback = Path(tempfile.gettempdir()) / "nirikshan"
    if _is_writable(fallback):
        log.warning(
            "%s is not writable, so the database is being kept at %s. On a "
            "serverless host this is expected: the file lives on temporary "
            "storage, is re-seeded on every cold start, and changes recorded "
            "during a session are not durable.",
            preferred,
            fallback,
        )
        return fallback

    raise RuntimeError(
        f"No writable directory is available for the SQLite database (tried "
        f"{preferred} and {fallback}). Set NIRIKSHAN_DATABASE_URL to point at "
        f"a database this process can reach."
    )


# An explicit URL wins, and when one is supplied no local directory is touched.
_URL_OVERRIDE = os.environ.get("NIRIKSHAN_DATABASE_URL")

if _URL_OVERRIDE:
    DATABASE_URL = _URL_OVERRIDE
    DB_DIR = None
    DB_PATH = (
        Path(DATABASE_URL[len(_SQLITE_PREFIX) :])
        if DATABASE_URL.startswith(_SQLITE_PREFIX)
        else DATABASE_URL
    )
else:
    DB_DIR = _resolve_db_dir()
    DB_PATH = DB_DIR / "nirikshan.db"
    DATABASE_URL = f"{_SQLITE_PREFIX}{DB_PATH}"

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
