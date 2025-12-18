"""Balance management cog for Discord Bits Wagering Bot."""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import config
from database.database import get_session, get_user, update_balance
from database.models import TransactionType
from utils.formatters import format_bits, format_balance_embed


class BalanceCog(commands.Cog):
    """Cog for managing user balances and daily rewards."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
    
    @app_commands.command(name="balance", description="Check your bits balance")
    async def balance(self, interaction: discord.Interaction):
        """Check user's bits balance."""
        async with get_session() as session:
            try:
                user = await get_user(session, interaction.user.id)
                embed = format_balance_embed(user, user.bits_balance)
                await interaction.response.send_message(embed=embed)
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Error retrieving balance: {str(e)}",
                    ephemeral=True
                )
    
    @app_commands.command(name="daily", description="Claim your daily reward of bits")
    async def daily(self, interaction: discord.Interaction):
        """Claim daily reward."""
        async with get_session() as session:
            try:
                user = await get_user(session, interaction.user.id)
                
                # Check if user can claim daily reward
                now = datetime.utcnow()
                if user.last_daily_reward:
                    time_since_last = now - user.last_daily_reward
                    if time_since_last < timedelta(days=1):
                        hours_remaining = 24 - (time_since_last.total_seconds() / 3600)
                        await interaction.response.send_message(
                            f"⏰ You've already claimed your daily reward today! "
                            f"Come back in {int(hours_remaining)} hours.",
                            ephemeral=True
                        )
                        return
                
                # Update last daily reward time
                user.last_daily_reward = now
                
                # Add daily reward
                new_balance = await update_balance(
                    session,
                    interaction.user.id,
                    config.DAILY_REWARD_AMOUNT,
                    TransactionType.DAILY_REWARD
                )
                
                embed = discord.Embed(
                    title="🎁 Daily Reward Claimed!",
                    description=f"You received {format_bits(config.DAILY_REWARD_AMOUNT)}!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="New Balance", value=format_bits(new_balance), inline=False)
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Error claiming daily reward: {str(e)}",
                    ephemeral=True
                )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(BalanceCog(bot))

