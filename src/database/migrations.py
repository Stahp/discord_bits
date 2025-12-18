"""Database migration utilities using Alembic."""
import asyncio
import logging
from alembic import command
from alembic.config import Config
from src import config

logger = logging.getLogger(__name__)


def run_migrations_sync():
    """Run Alembic migrations synchronously."""
    try:
        # Get Alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Set database URL (use sync URL for Alembic)
        database_url = config.DATABASE_URL
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        
        # Run migrations
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise


async def run_migrations():
    """Run Alembic migrations asynchronously (wrapper for sync function)."""
    # Run in executor since Alembic commands are synchronous
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_migrations_sync)
