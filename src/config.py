"""Configuration settings for the Discord bot."""
import os
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/discord_bits_bot")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Bot Configuration
DAILY_REWARD_AMOUNT = int(os.getenv("DAILY_REWARD_AMOUNT", "100"))
STARTING_BALANCE = int(os.getenv("STARTING_BALANCE", "1000"))
MIN_BET_AMOUNT = int(os.getenv("MIN_BET_AMOUNT", "10"))

# Admin Configuration
ADMIN_ROLE_IDS = [
    int(role_id.strip())
    for role_id in os.getenv("ADMIN_ROLE_IDS", "").split(",")
    if role_id.strip()
]

# Bot Settings
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "/")

# Wager Channel Configuration
WAGER_CHANNEL_ID = os.getenv("WAGER_CHANNEL_ID", None)
if WAGER_CHANNEL_ID:
    WAGER_CHANNEL_ID = int(WAGER_CHANNEL_ID)

