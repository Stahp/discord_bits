# Discord Bits Wagering Bot

A Discord bot that allows users to create and participate in wagers using bits (virtual currency), similar to Twitch's bit wagering system.

## Features

- 💰 **Balance Management**: Users start with 1000 bits and can claim daily rewards
- 🎲 **Wager Creation**: Users can create wagers with multiple choice options
- 🎯 **Betting System**: Place bets on active wagers with proportional payout distribution
- ⚙️ **Admin Controls**: Admins can resolve wagers and manage user balances
- 📊 **Transaction History**: All transactions are logged for audit purposes

## Prerequisites

- Python 3.9 or higher (for local development)
- PostgreSQL database (or use Docker Compose)
- Discord Bot Token (from [Discord Developer Portal](https://discord.com/developers/applications))
- Docker and Docker Compose (for containerized deployment)

## Installation

### Option 1: Docker (Recommended)

The easiest way to run the bot is using Docker Compose, which sets up both the bot and PostgreSQL database automatically.

1. **Clone or download this repository**

2. **Create a `.env` file** in the project root (you can copy from `.env.example`):
```env
DISCORD_TOKEN=your_discord_bot_token_here
POSTGRES_PASSWORD=your_secure_password_here
DAILY_REWARD_AMOUNT=100
STARTING_BALANCE=1000
MIN_BET_AMOUNT=10
ADMIN_ROLE_IDS=123456789012345678,987654321098765432
```

3. **Build and start the containers**:
```bash
docker-compose up -d
```

4. **View logs**:
```bash
docker-compose logs -f bot
```

5. **Stop the containers**:
```bash
docker-compose down
```

**Note**: The database schema will be automatically initialized when the bot starts for the first time.

### Option 2: Local Installation

1. **Clone or download this repository**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up your PostgreSQL database**:
```bash
# Create a database (example)
createdb discord_bits_bot
```

4. **Create a `.env` file** in the project root (you can copy from `.env.example`):
```env
DISCORD_TOKEN=your_discord_bot_token_here
DATABASE_URL=postgresql://username:password@localhost:5432/discord_bits_bot
DAILY_REWARD_AMOUNT=100
STARTING_BALANCE=1000
MIN_BET_AMOUNT=10
ADMIN_ROLE_IDS=123456789012345678,987654321098765432
```

5. **Initialize the database** (migrations run automatically on bot startup):
```bash
# Or manually run migrations:
python -m alembic upgrade head
```

6. **Run the bot**:
```bash
python -m src.bot
```

## Commands

### User Commands

- `/balance` - Check your bits balance
- `/daily` - Claim your daily reward (100 bits)
- `/createwager <title> <options> [description]` - Create a new wager
- `/wagers` - List all active wagers
- `/wagerinfo <wager_id>` - View details of a specific wager
- `/bet <wager_id> <option> <amount>` - Place a bet on a wager
- `/mybets` - View your active bets
- `/help` - Show help information

### Admin Commands

- `/resolve <wager_id> <winning_option>` - Resolve a wager and distribute winnings
- `/admin_balance <user> <amount>` - Adjust a user's balance
- `/admin_close <wager_id>` - Close a wager to prevent new bets
- `/set_wager_channel <channel>` - Set the channel for wager messages

## How It Works

1. **Getting Bits**: New users start with 1000 bits. Users can claim 100 bits daily using `/daily`.

2. **Creating Wagers**: Users can create wagers with 2-10 options. Each wager has a title, optional description, and multiple choice options.

3. **Placing Bets**: Users can place bets on any open wager by selecting an option and betting amount (minimum 10 bits). Each user can only place one bet per wager.

4. **Resolving Wagers**: Admins resolve wagers by selecting the winning option. Winnings are distributed proportionally:
   - Total pool is calculated from all bets
   - Winners receive: `(their_bet / total_winning_pool) * total_pool`
   - If no one bet on the winning option, all bets are refunded

## Configuration

Edit the `.env` file to configure:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DISCORD_TOKEN` | Your Discord bot token | - | ✅ Yes |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://localhost/discord_bits_bot` | ✅ Yes |
| `POSTGRES_PASSWORD` | PostgreSQL password (Docker only) | `changeme` | No |
| `DAILY_REWARD_AMOUNT` | Bits given daily | `100` | No |
| `STARTING_BALANCE` | New user starting balance | `1000` | No |
| `MIN_BET_AMOUNT` | Minimum bet amount | `10` | No |
| `ADMIN_ROLE_IDS` | Comma-separated Discord role IDs for admin commands | - | No |

## Database Schema

The bot uses PostgreSQL with the following tables:

- **users**: User balances and daily reward tracking
- **wagers**: Active and resolved wagers
- **bets**: Individual bets placed on wagers
- **transactions**: Audit log for all bit transactions
- **guild_settings**: Server-specific settings (wager channel, etc.)

### Database Migrations

This project uses **Alembic** for database migrations. Migrations run automatically when the bot starts.

**Manual migration commands:**
```bash
# Create a new migration from model changes
python -m alembic revision --autogenerate -m "Description of changes"

# Apply all pending migrations
python -m alembic upgrade head

# Rollback one migration
python -m alembic downgrade -1

# View migration history
python -m alembic history

# View current database version
python -m alembic current
```

## Docker Commands

### Build the Docker image
```bash
docker-compose build
```

### Start services
```bash
docker-compose up -d
```

### View logs
```bash
# All services
docker-compose logs -f

# Bot only
docker-compose logs -f bot

# PostgreSQL only
docker-compose logs -f postgres
```

### Stop services
```bash
docker-compose down
```

### Stop and remove volumes (deletes database data)
```bash
docker-compose down -v
```

### Restart the bot
```bash
docker-compose restart bot
```

### Rebuild after code changes
```bash
docker-compose build bot
docker-compose up -d bot
```

### Access PostgreSQL directly
```bash
docker-compose exec postgres psql -U discord_bits -d discord_bits_bot
```

## Bot Permissions

When inviting the bot to your Discord server, you need to grant the following permissions:

### Required Permissions (Minimum)

These permissions are **essential** for the bot to function:

1. **Send Messages** - Required to send wager messages and command responses
2. **Manage Messages** - Required to pin wager messages
3. **Read Message History** - Required to fetch and update existing messages
4. **View Channels** - Required to see channels
5. **Read Messages** - Required to read message content

### Optional Permissions

- **Manage Channels** - Only needed if you want the bot to automatically create a wager channel. If you manually set a channel using `/set_wager_channel`, this permission is **not required**.

### How to Set Permissions

#### Method 1: When Inviting the Bot (Recommended)

When generating the bot invite URL in the Discord Developer Portal:

1. Go to https://discord.com/developers/applications
2. Select your bot application
3. Click on **OAuth2** in the left sidebar
4. Click on **URL Generator** tab
5. Under **SCOPES**, check:
   - ✅ **bot**
6. Under **BOT PERMISSIONS**, check:
   - ✅ **Send Messages**
   - ✅ **Manage Messages**
   - ✅ **Read Message History**
   - ✅ **View Channels**
   - ✅ **Read Messages**
   - (Optional) ✅ **Manage Channels** (only if you want auto channel creation)
7. Copy the generated URL at the bottom of the page
8. Open the URL in your browser
9. Select your Discord server and click **Authorize**

**Note**: You do **NOT** need to grant the "Administrator" permission. The bot only needs the specific permissions listed above.

#### Method 2: After Bot is Already in Server

If the bot is already in your server but missing permissions:

1. Right-click on your Discord server name
2. Select **Server Settings**
3. Go to **Roles** in the left sidebar
4. Find the bot's role (usually named after your bot)
5. Scroll down to **Permissions** section
6. Enable the following permissions:
   - ✅ **View Channels**
   - ✅ **Read Messages**
   - ✅ **Send Messages**
   - ✅ **Read Message History**
   - ✅ **Manage Messages**
   - (Optional) ✅ **Manage Channels**
7. Click **Save Changes**

**Note**: Make sure the bot's role is positioned high enough in the role hierarchy (above other roles if needed) and that channel-specific permissions don't override these settings.

#### Method 3: Direct Invite URL (Advanced)

You can also create an invite URL manually using the permission value:

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=67584&scope=bot
```

Replace `YOUR_BOT_CLIENT_ID` with your bot's Client ID (found in the **General Information** page of your Discord application).

**Permission Value**: `67584` (0x10800 in hex) - This includes all required permissions except "Manage Channels"

## Troubleshooting

### Bot doesn't respond to commands
- Make sure the bot has the necessary permissions in your Discord server
- Check that slash commands are synced (check bot startup logs)
- Verify the bot token is correct

### Database connection errors
- Ensure PostgreSQL is running
- Verify the DATABASE_URL is correct
- Check that the database exists and is accessible
- For Docker: Wait for PostgreSQL to be healthy (`docker-compose ps`)

### Permission errors
- Admin commands require either administrator permission or roles listed in ADMIN_ROLE_IDS
- Make sure the bot has the necessary Discord permissions (see Bot Permissions section above)
- If you see "I don't have permission to send messages" errors, grant the bot "Send Messages" permission in that channel
- If you see "I don't have permission to pin messages" errors, grant the bot "Manage Messages" permission in that channel

### Bot container exits immediately
- Check logs: `docker-compose logs bot`
- Verify `DISCORD_TOKEN` is set correctly
- Ensure PostgreSQL is running: `docker-compose ps`

### Port conflicts
- If port 5432 is already in use, modify `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"  # Use 5433 on host instead
```

## Project Structure

```
DISCORD/
├── src/                   # Source code package
│   ├── bot.py             # Main bot entry point
│   ├── config.py           # Configuration settings
│   ├── cogs/              # Bot command modules
│   │   ├── balance.py      # Balance commands
│   │   ├── wagers.py      # Wager commands
│   │   ├── betting.py     # Betting commands
│   │   ├── admin.py       # Admin commands
│   │   └── help.py        # Help command
│   ├── database/          # Database code
│   │   ├── database.py    # Database connection and utilities
│   │   ├── models.py      # SQLAlchemy models
│   │   ├── migrations.py  # Migration utilities
│   │   └── migrations/    # Legacy migration scripts (deprecated)
│   └── utils/             # Utility functions
│       ├── formatters.py  # Message formatting
│       └── validators.py  # Input validation
├── alembic/               # Alembic migration scripts
├── alembic.ini            # Alembic migration configuration
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose configuration
└── README.md              # This file
```

## Production Considerations

1. **Change default password**: Set a strong `POSTGRES_PASSWORD` in production
2. **Use secrets management**: Consider using Docker secrets or a secrets manager
3. **Backup database**: Regularly backup the `postgres_data` volume
4. **Monitor logs**: Set up log aggregation for production
5. **Resource limits**: Add resource limits to `docker-compose.yml`:
```yaml
services:
  bot:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

## License

This project is provided as-is for educational and personal use.
