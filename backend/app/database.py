"""Database engine, session and automatic initialization."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


def _build_engine() -> Engine:
    connect_args = {}
    kwargs = {"pool_pre_ping": True, "future": True}
    if settings.database_url.startswith("sqlite"):
        # Allow cross-thread access for FastAPI background tasks.
        connect_args = {"check_same_thread": False}
        if ":memory:" in settings.database_url:
            # In-memory SQLite is per-connection by default; use a single
            # shared connection so all sessions see the same tables. This is
            # what makes the in-memory test database work with TestClient.
            kwargs["poolclass"] = StaticPool
    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        **kwargs,
    )

    # Make SQLite enforce foreign keys.
    if settings.database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_connection, _):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db() -> None:
    """Create all tables. Called once on application startup."""
    from . import models  # noqa: F401  (import so models register on Base)

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised: %s", settings.database_url)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Iterator[Session]:
    """Context manager for use outside of FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
