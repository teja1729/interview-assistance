"""Alembic uses the same environment configuration as the API and worker."""

from alembic import context
from sqlmodel import SQLModel

from app import models  # noqa: F401 - registers every table for autogeneration
from app.config import settings
from app.db import make_engine

config = context.config
target_metadata = SQLModel.metadata

if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(settings.database_url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=engine.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
