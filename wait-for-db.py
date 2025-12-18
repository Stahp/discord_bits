"""Wait for database to be ready."""
import asyncio
import sys
from sqlalchemy import text
from database.database import engine


async def check_db():
    """Check if database is ready."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        return True
    except Exception as e:
        print(f"Database check failed: {e}")
        return False


async def wait_for_db():
    """Wait for database to be ready."""
    max_attempts = 30
    for attempt in range(max_attempts):
        if await check_db():
            print("Database is ready!")
            return True
        print(f"Waiting for database... ({attempt + 1}/{max_attempts})")
        await asyncio.sleep(1)
    print("Database connection timeout!")
    return False


if __name__ == "__main__":
    success = asyncio.run(wait_for_db())
    sys.exit(0 if success else 1)

