"""Alembic migration environment — async-compatible with SQLAlchemy 2.0."""
import asyncio
from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Add project root to sys.path so app modules are importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import all models to register them with metadata
from app.database.base import Base  # noqa: E402
from app.config.settings import settings  # noqa: E402
import app.models  # noqa: E402, F401 — registers all models with Base.metadata

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use model metadata for autogenerate
target_metadata = Base.metadata


def get_url() -> str:
    """Return sync database URL for Alembic (uses psycopg2)."""
    return settings.DATABASE_URL_SYNC


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (outputs SQL)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (for asyncpg compatibility)."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
