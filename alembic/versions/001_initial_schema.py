"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # Check if tables exist before creating them (idempotent migration)
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Create users table
    if 'users' not in existing_tables:
        op.create_table('users',
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('bits_balance', sa.Integer(), nullable=False, server_default='1000'),
            sa.Column('last_daily_reward', sa.TIMESTAMP(), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('user_id')
        )
    
    # Create wagers table
    if 'wagers' not in existing_tables:
        op.create_table('wagers',
            sa.Column('wager_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('creator_id', sa.BigInteger(), nullable=False),
            sa.Column('title', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='open'),
            sa.Column('winning_option', sa.Integer(), nullable=True),
            sa.Column('message_id', sa.BigInteger(), nullable=True),
            sa.Column('channel_id', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
            sa.Column('resolved_at', sa.TIMESTAMP(), nullable=True),
            sa.ForeignKeyConstraint(['creator_id'], ['users.user_id'], ),
            sa.PrimaryKeyConstraint('wager_id')
        )
    
    # Create bets table
    if 'bets' not in existing_tables:
        op.create_table('bets',
            sa.Column('bet_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('wager_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('option_index', sa.Integer(), nullable=False),
            sa.Column('amount', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
            sa.ForeignKeyConstraint(['wager_id'], ['wagers.wager_id'], ),
            sa.PrimaryKeyConstraint('bet_id'),
            sa.CheckConstraint('amount > 0', name='check_positive_amount'),
            sa.CheckConstraint('option_index >= 0', name='check_valid_option_index')
        )
    
    # Create transactions table
    if 'transactions' not in existing_tables:
        op.create_table('transactions',
            sa.Column('transaction_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('amount', sa.Integer(), nullable=False),
            sa.Column('transaction_type', sa.String(30), nullable=False),
            sa.Column('reference_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
            sa.PrimaryKeyConstraint('transaction_id')
        )
    
    # Create guild_settings table
    if 'guild_settings' not in existing_tables:
        op.create_table('guild_settings',
            sa.Column('guild_id', sa.BigInteger(), nullable=False),
            sa.Column('wager_channel_id', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('guild_id')
        )


def downgrade() -> None:
    op.drop_table('guild_settings')
    op.drop_table('transactions')
    op.drop_table('bets')
    op.drop_table('wagers')
    op.drop_table('users')
