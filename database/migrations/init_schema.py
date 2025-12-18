"""Initial database schema migration."""
import asyncio
from sqlalchemy import text
from database.database import engine, init_db


async def run_migration():
    """Run the initial schema migration."""
    print("Creating database tables...")
    await init_db()
    print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())

