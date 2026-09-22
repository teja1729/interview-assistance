"""Database connection only. Schema changes belong in Alembic migrations."""

from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, create_engine

from .config import settings


def make_engine(url: str):
    if url.startswith("sqlite:///"):
        path = url.removeprefix("sqlite:///")
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"check_same_thread": False, "timeout": 15} if url.startswith("sqlite") else {},
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def pragmas(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=15000")

    return engine


engine = make_engine(settings.database_url)


def get_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session
