"""Database connection management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Engine for source database (read-only)
source_engine = create_engine(settings.database_url, pool_pre_ping=True)
SourceSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=source_engine)

# Engine for RAG database
rag_engine = create_engine(settings.rag_database_url, pool_pre_ping=True)
RagSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rag_engine)


@contextmanager
def get_source_db() -> Generator[Session, None, None]:
    """Get source database session (read-only)."""
    db = SourceSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_rag_db() -> Generator[Session, None, None]:
    """Get RAG database session."""
    db = RagSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_rag_db() -> None:
    """Initialize RAG database tables."""
    from app.models.base import Base
    from app.models.graph import Post, Relationship  # noqa: F401

    Base.metadata.create_all(bind=rag_engine)
