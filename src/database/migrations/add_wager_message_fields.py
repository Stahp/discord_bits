"""Migration to add message_id and channel_id fields to wagers table."""
import asyncio
from sqlalchemy import text
from database.database import engine


async def run_migration():
    """Add message_id and channel_id columns to wagers table if they don't exist."""
    async with engine.begin() as conn:
        # Check if columns exist
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='wagers' AND column_name='message_id'
        """))
        
        if result.scalar_one_or_none() is None:
            print("Adding message_id column to wagers table...")
            await conn.execute(text("ALTER TABLE wagers ADD COLUMN message_id BIGINT"))
            print("✓ Added message_id column")
        else:
            print("message_id column already exists")
        
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='wagers' AND column_name='channel_id'
        """))
        
        if result.scalar_one_or_none() is None:
            print("Adding channel_id column to wagers table...")
            await conn.execute(text("ALTER TABLE wagers ADD COLUMN channel_id BIGINT"))
            print("✓ Added channel_id column")
        else:
            print("channel_id column already exists")
    
    print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())
