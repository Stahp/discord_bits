"""Database connection and setup for the Discord Bits Wagering Bot."""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from src import config
from src.database.models import Base

# Create async engine for PostgreSQL
# Convert postgresql:// to postgresql+asyncpg:// for async support
async_database_url = config.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    async_database_url,
    poolclass=NullPool,
    echo=False
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_session():
    """Get an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_user(session, user_id: int):
    """Get or create a user."""
    from src.database.models import User
    from sqlalchemy import select
    
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        user = User(user_id=user_id, bits_balance=config.STARTING_BALANCE)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user


async def update_balance(session, user_id: int, amount: int, transaction_type, reference_id=None):
    """Update user balance and create a transaction record."""
    from src.database.models import User, Transaction
    from sqlalchemy import select
    
    user = await get_user(session, user_id)
    user.bits_balance += amount
    
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        reference_id=reference_id
    )
    session.add(transaction)
    await session.commit()
    
    return user.bits_balance

