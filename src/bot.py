"""Main bot entry point for Discord Bits Wagering Bot."""
import asyncio
import logging
import discord
from discord.ext import commands
from src import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
bot = commands.Bot(
    command_prefix=config.COMMAND_PREFIX,
    intents=intents,
    help_command=None  # We'll create a custom help command
)


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guild(s)')
    
    # Load cogs
    cogs_to_load = [
        'src.cogs.balance',
        'src.cogs.wagers',
        'src.cogs.betting',
        'src.cogs.admin',
        'src.cogs.help'
    ]
    
    for cog in cogs_to_load:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded cog: {cog}")
        except Exception as e:
            logger.error(f"Failed to load cog {cog}: {e}")
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    
    # Register persistent views for existing wagers
    try:
        from src.database.database import get_session
        from src.database.models import Wager, WagerStatus
        from sqlalchemy import select
        from src.cogs.betting import WagerOptionView
        
        async with get_session() as session:
            # Get all open wagers with pinned messages
            result = await session.execute(
                select(Wager)
                .where(Wager.status == WagerStatus.OPEN)
                .where(Wager.message_id.isnot(None))
                .where(Wager.channel_id.isnot(None))
            )
            wagers = result.scalars().all()
            
            registered_count = 0
            for wager in wagers:
                try:
                    # Verify message still exists
                    channel = bot.get_channel(wager.channel_id)
                    if channel:
                        try:
                            message = await channel.fetch_message(wager.message_id)
                            # Recreate and register the view
                            view = WagerOptionView(wager.wager_id, wager.options, bot)
                            bot.add_view(view, message_id=wager.message_id)
                            registered_count += 1
                        except discord.NotFound:
                            logger.warning(f"Wager {wager.wager_id} message {wager.message_id} not found, clearing from database")
                            wager.message_id = None
                            wager.channel_id = None
                            await session.commit()
                        except discord.Forbidden:
                            logger.warning(f"No permission to fetch message {wager.message_id} for wager {wager.wager_id}")
                except Exception as e:
                    logger.error(f"Error registering view for wager {wager.wager_id}: {e}")
            
            if registered_count > 0:
                logger.info(f"Registered {registered_count} persistent view(s) for active wagers")
    except Exception as e:
        logger.error(f"Failed to register persistent views: {e}", exc_info=True)


@bot.event
async def on_command_error(ctx, error):
    """Global error handler."""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore command not found errors
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
        return
    
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument: {str(error)}")
        return
    
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"❌ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
        return
    
    logger.error(f"Unhandled error in command {ctx.command}: {error}", exc_info=error)
    await ctx.send("❌ An unexpected error occurred. Please try again later.")


@bot.event
async def on_application_command_error(ctx, error):
    """Global error handler for slash commands."""
    if isinstance(error, discord.app_commands.CommandInvokeError):
        original_error = error.original
        logger.error(f"Error in slash command {ctx.command.name}: {original_error}", exc_info=original_error)
        
        if isinstance(original_error, ValueError):
            await ctx.response.send_message(f"❌ {str(original_error)}", ephemeral=True)
        elif isinstance(original_error, PermissionError):
            await ctx.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            await ctx.response.send_message("❌ An unexpected error occurred. Please try again later.", ephemeral=True)
    else:
        logger.error(f"Unhandled error in slash command {ctx.command.name}: {error}", exc_info=error)
        await ctx.response.send_message("❌ An unexpected error occurred. Please try again later.", ephemeral=True)


def main():
    """Main entry point."""
    if not config.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set in environment variables")
        return
    
    try:
        bot.run(config.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()

