from logging.config import fileConfig
import asyncio
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection

from alembic import context

# Import your models
import sys
import os
from pathlib import Path
# Add project root and src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.database.models import Base

# Get database URL from environment (don't import config to avoid DISCORD_TOKEN requirement)
database_url = os.getenv("DATABASE_URL", "postgresql://localhost/discord_bits_bot")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
alembic_cfg = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if alembic_cfg.config_file_name is not None:
    fileConfig(alembic_cfg.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Set the database URL
# Use sync URL for Alembic (it uses sync connections)
# Ensure we use psycopg2 (sync), not asyncpg
sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
alembic_cfg.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use sync engine for Alembic (Alembic commands are synchronous)
    # The actual application uses async, but migrations run sync
    connectable = create_engine(
        alembic_cfg.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
