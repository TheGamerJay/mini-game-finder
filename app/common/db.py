"""Database session management for clean architecture."""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _normalize_db_url(url: str | None) -> str | None:
    """Normalize database URL for SQLAlchemy compatibility."""
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


# Database configuration
DATABASE_URL = _normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///local.db"))

# SQLAlchemy 2.x engine configuration
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=30,
    future=True,
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic transaction handling.

    Usage:
        with db_session() as session:
            # Your database operations here
            pass  # Automatically commits on success, rolls back on exception
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Session:
    """
    Get a database session for dependency injection.

    Note: Caller is responsible for closing the session.
    """
    return SessionLocal()