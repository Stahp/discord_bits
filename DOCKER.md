# Docker Deployment Guide

## Quick Start

1. **Create a `.env` file** with your configuration:
```env
DISCORD_TOKEN=your_discord_bot_token_here
POSTGRES_PASSWORD=your_secure_password_here
DAILY_REWARD_AMOUNT=100
STARTING_BALANCE=1000
MIN_BET_AMOUNT=10
ADMIN_ROLE_IDS=123456789012345678,987654321098765432
```

2. **Start the services**:
```bash
docker-compose up -d
```

3. **View logs**:
```bash
docker-compose logs -f bot
```

That's it! The bot will automatically:
- Wait for PostgreSQL to be ready
- Initialize the database schema
- Start the Discord bot

## Docker Compose Services

### PostgreSQL Service
- **Image**: `postgres:15-alpine`
- **Port**: `5432` (exposed to host)
- **Database**: `discord_bits_bot`
- **User**: `discord_bits`
- **Password**: Set via `POSTGRES_PASSWORD` in `.env`
- **Data Persistence**: Stored in Docker volume `postgres_data`

### Bot Service
- **Built from**: Local `Dockerfile`
- **Depends on**: PostgreSQL (waits for health check)
- **Restart Policy**: `unless-stopped`
- **Environment**: All config from `.env` file

## Common Commands

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

### Stop and remove all data (⚠️ deletes database)
```bash
docker-compose down -v
```

### Restart bot
```bash
docker-compose restart bot
```

### Rebuild after code changes
```bash
docker-compose build bot
docker-compose up -d bot
```

### Access PostgreSQL shell
```bash
docker-compose exec postgres psql -U discord_bits -d discord_bits_bot
```

## Environment Variables

All environment variables are read from the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token (required) | - |
| `POSTGRES_PASSWORD` | PostgreSQL password | `changeme` |
| `DAILY_REWARD_AMOUNT` | Bits given daily | `100` |
| `STARTING_BALANCE` | New user starting balance | `1000` |
| `MIN_BET_AMOUNT` | Minimum bet amount | `10` |
| `ADMIN_ROLE_IDS` | Comma-separated role IDs | - |

## Troubleshooting

### Bot container exits immediately
- Check logs: `docker-compose logs bot`
- Verify `DISCORD_TOKEN` is set correctly
- Ensure PostgreSQL is running: `docker-compose ps`

### Database connection errors
- Wait for PostgreSQL to be healthy: `docker-compose ps`
- Check PostgreSQL logs: `docker-compose logs postgres`
- Verify `POSTGRES_PASSWORD` matches in `.env` and `DATABASE_URL`

### Permission errors
- The bot runs as a non-root user (`botuser`) for security
- If you need to modify files, ensure proper permissions

### Port conflicts
- If port 5432 is already in use, modify `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"  # Use 5433 on host instead
```

## Production Considerations

1. **Change default password**: Set a strong `POSTGRES_PASSWORD`
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



