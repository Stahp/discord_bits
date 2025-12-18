"""Migration to add guild_settings table."""
import asyncio
from sqlalchemy import text
from database.database import engine


async def run_migration():
    """Create guild_settings table if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='guild_settings'
        """))
        
        if result.scalar_one_or_none() is None:
            print("Creating guild_settings table...")
            await conn.execute(text("""
                CREATE TABLE guild_settings (
                    guild_id BIGINT PRIMARY KEY,
                    wager_channel_id BIGINT,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("✓ Created guild_settings table")
        else:
            print("guild_settings table already exists")
    
    print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())
