"""Database engine factory.

Default: SQLite at ./data/scriptmurder.db (created on demand).
Production: set SM_DATABASE_URL, e.g. postgresql+psycopg://user:pass@host/db
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import Settings
from app.core.persistence.models import Base

DEFAULT_SQLITE_URL = "sqlite:///./data/scriptmurder.db"


def make_engine(url: str | None = None) -> Engine:
    url = url or Settings().database_url or DEFAULT_SQLITE_URL
    if url.startswith("sqlite") and ":memory:" not in url:
        # ensure the parent directory exists for file-based SQLite
        db_file = url.removeprefix("sqlite:///")
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return engine
