"""SQLAlchemy models for the Discord Bits Wagering Bot."""
from sqlalchemy import (
    BigInteger, Integer, Text, TIMESTAMP, ForeignKey, String,
    func, CheckConstraint, Column
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# Wager status constants
WAGER_STATUS_OPEN = "open"
WAGER_STATUS_CLOSED = "closed"
WAGER_STATUS_RESOLVED = "resolved"

# Transaction type constants
TRANSACTION_TYPE_DAILY_REWARD = "daily_reward"
TRANSACTION_TYPE_BET_PLACED = "bet_placed"
TRANSACTION_TYPE_BET_WON = "bet_won"
TRANSACTION_TYPE_BET_REFUNDED = "bet_refunded"
TRANSACTION_TYPE_ADMIN_ADJUSTMENT = "admin_adjustment"

# Valid values for validation
VALID_WAGER_STATUSES = {WAGER_STATUS_OPEN, WAGER_STATUS_CLOSED, WAGER_STATUS_RESOLVED}
VALID_TRANSACTION_TYPES = {
    TRANSACTION_TYPE_DAILY_REWARD,
    TRANSACTION_TYPE_BET_PLACED,
    TRANSACTION_TYPE_BET_WON,
    TRANSACTION_TYPE_BET_REFUNDED,
    TRANSACTION_TYPE_ADMIN_ADJUSTMENT
}


def validate_wager_status(status: str) -> str:
    """Validate wager status value."""
    if status not in VALID_WAGER_STATUSES:
        raise ValueError(f"Invalid wager status: {status}. Must be one of {VALID_WAGER_STATUSES}")
    return status


def validate_transaction_type(transaction_type: str) -> str:
    """Validate transaction type value."""
    if transaction_type not in VALID_TRANSACTION_TYPES:
        raise ValueError(f"Invalid transaction type: {transaction_type}. Must be one of {VALID_TRANSACTION_TYPES}")
    return transaction_type


class User(Base):
    """User model for storing user balances and daily reward tracking."""
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True)
    bits_balance = Column(Integer, default=1000, nullable=False)
    last_daily_reward = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    wagers_created = relationship("Wager", back_populates="creator", foreign_keys="[Wager.creator_id]")
    bets = relationship("Bet", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, bits_balance={self.bits_balance})>"


class Wager(Base):
    """Wager model for storing active and resolved wagers."""
    __tablename__ = "wagers"

    wager_id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    options = Column(JSONB, nullable=False)  # Array of choice options
    status = Column(String(20), default=WAGER_STATUS_OPEN, nullable=False)
    winning_option = Column(Integer, nullable=True)
    message_id = Column(BigInteger, nullable=True)  # Discord message ID of pinned wager message
    channel_id = Column(BigInteger, nullable=True)  # Discord channel ID where message is posted
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    resolved_at = Column(TIMESTAMP, nullable=True)

    # Relationships
    creator = relationship("User", back_populates="wagers_created", foreign_keys=[creator_id])
    bets = relationship("Bet", back_populates="wager", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Wager(wager_id={self.wager_id}, title={self.title}, status={self.status})>"


class Bet(Base):
    """Bet model for storing individual bets placed on wagers."""
    __tablename__ = "bets"

    bet_id = Column(Integer, primary_key=True, autoincrement=True)
    wager_id = Column(Integer, ForeignKey("wagers.wager_id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    option_index = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    wager = relationship("Wager", back_populates="bets")
    user = relationship("User", back_populates="bets")

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_positive_amount"),
        CheckConstraint("option_index >= 0", name="check_valid_option_index"),
    )

    def __repr__(self):
        return f"<Bet(bet_id={self.bet_id}, wager_id={self.wager_id}, user_id={self.user_id}, amount={self.amount})>"


class Transaction(Base):
    """Transaction model for audit log of all bit transactions."""
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    amount = Column(Integer, nullable=False)  # Positive for credits, negative for debits
    transaction_type = Column(String(30), nullable=False)
    reference_id = Column(Integer, nullable=True)  # Links to bet_id or wager_id
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(transaction_id={self.transaction_id}, user_id={self.user_id}, amount={self.amount}, type={self.transaction_type})>"


class GuildSettings(Base):
    """Guild-specific settings."""
    __tablename__ = "guild_settings"

    guild_id = Column(BigInteger, primary_key=True)
    wager_channel_id = Column(BigInteger, nullable=True)  # Channel ID for wager messages
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<GuildSettings(guild_id={self.guild_id}, wager_channel_id={self.wager_channel_id})>"

