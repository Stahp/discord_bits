"""Admin cog for Discord Bits Wagering Bot."""
import discord
from discord.ext import commands
from discord import app_commands
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from src import config
from src.database.database import get_session, get_user, update_balance
from src.database.models import (
    Wager, Bet, WAGER_STATUS_OPEN, WAGER_STATUS_CLOSED, WAGER_STATUS_RESOLVED,
    TRANSACTION_TYPE_BET_REFUNDED, TRANSACTION_TYPE_BET_WON, TRANSACTION_TYPE_ADMIN_ADJUSTMENT,
    GuildSettings
)
from src.utils.formatters import format_bits, format_wager_embed
from src.cogs.betting import update_wager_message
from sqlalchemy import select


def is_admin(interaction: discord.Interaction) -> bool:
    """Check if user is an admin."""
    if not config.ADMIN_ROLE_IDS:
        # If no admin roles configured, check for administrator permission
        return interaction.user.guild_permissions.administrator
    
    user_roles = [role.id for role in interaction.user.roles]
    return any(role_id in user_roles for role_id in config.ADMIN_ROLE_IDS)


class AdminCog(commands.Cog):
    """Cog for admin commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="resolve", description="Resolve a wager and distribute winnings (Admin only)")
    @app_commands.describe(
        wager_id="The ID of the wager to resolve",
        winning_option="The winning option number (1-based index)"
    )
    async def resolve(
        self,
        interaction: discord.Interaction,
        wager_id: int,
        winning_option: int
    ):
        """Resolve a wager and distribute winnings."""
        if not is_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        # Convert to 0-based index
        option_index = winning_option - 1
        if option_index < 0:
            await interaction.response.send_message(
                "❌ Option number must be at least 1.",
                ephemeral=True
            )
            return
        
        async with get_session() as session:
            try:
                # Get wager with bets
                result = await session.execute(
                    select(Wager)
                    .options(selectinload(Wager.bets))
                    .where(Wager.wager_id == wager_id)
                )
                wager = result.scalar_one_or_none()
                
                if not wager:
                    await interaction.response.send_message(
                        f"❌ Wager with ID {wager_id} not found.",
                        ephemeral=True
                    )
                    return
                
                if wager.status == WAGER_STATUS_RESOLVED:
                    await interaction.response.send_message(
                        "❌ This wager has already been resolved.",
                        ephemeral=True
                    )
                    return
                
                # Validate option index
                if option_index >= len(wager.options):
                    await interaction.response.send_message(
                        f"❌ Invalid option. This wager has {len(wager.options)} option(s).",
                        ephemeral=True
                    )
                    return
                
                # Check if there are any bets
                if not wager.bets:
                    await interaction.response.send_message(
                        "❌ This wager has no bets. Cannot resolve.",
                        ephemeral=True
                    )
                    return
                
                # Calculate pools
                total_pool = sum(bet.amount for bet in wager.bets)
                winning_bets = [bet for bet in wager.bets if bet.option_index == option_index]
                losing_bets = [bet for bet in wager.bets if bet.option_index != option_index]
                
                if not winning_bets:
                    # No winners - refund all bets
                    await interaction.response.defer()
                    
                    for bet in wager.bets:
                        await update_balance(
                            session,
                            bet.user_id,
                            bet.amount,
                            TRANSACTION_TYPE_BET_REFUNDED,
                            reference_id=bet.bet_id
                        )
                    
                    wager.status = WAGER_STATUS_RESOLVED
                    wager.winning_option = option_index
                    wager.resolved_at = datetime.utcnow()
                    await session.commit()
                    
                    # Update pinned message if it exists
                    await update_wager_message(self.bot, wager_id)
                    
                    embed = discord.Embed(
                        title="🎲 Wager Resolved",
                        description=f"**{wager.title}**\n\nNo one bet on the winning option. All bets have been refunded.",
                        color=discord.Color.orange()
                    )
                    embed.add_field(
                        name="Winning Option",
                        value=f"Option {winning_option}: {wager.options[option_index]}",
                        inline=False
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                # Calculate winning pool
                winning_pool = sum(bet.amount for bet in winning_bets)
                
                # Distribute winnings proportionally
                await interaction.response.defer()
                
                winners_info = []
                for bet in winning_bets:
                    # Calculate payout: (bet_amount / winning_pool) * total_pool
                    payout = int((bet.amount / winning_pool) * total_pool)
                    
                    # Update balance
                    new_balance = await update_balance(
                        session,
                        bet.user_id,
                        payout,
                        TRANSACTION_TYPE_BET_WON,
                        reference_id=bet.bet_id
                    )
                    
                    winners_info.append({
                        "user_id": bet.user_id,
                        "bet_amount": bet.amount,
                        "payout": payout
                    })
                
                # Update wager status
                wager.status = WAGER_STATUS_RESOLVED
                wager.winning_option = option_index
                wager.resolved_at = datetime.utcnow()
                await session.commit()
                
                # Update pinned message if it exists
                await update_wager_message(self.bot, wager_id)
                
                # Create result embed
                embed = discord.Embed(
                    title="🎉 Wager Resolved!",
                    description=f"**{wager.title}**",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name="🏆 Winning Option",
                    value=f"Option {winning_option}: {wager.options[option_index]}",
                    inline=False
                )
                embed.add_field(
                    name="💰 Total Pool",
                    value=format_bits(total_pool),
                    inline=True
                )
                embed.add_field(
                    name="👥 Winners",
                    value=str(len(winning_bets)),
                    inline=True
                )
                
                # Add winner details (limit to first 10)
                winners_text = ""
                for winner in winners_info[:10]:
                    user = self.bot.get_user(winner["user_id"])
                    username = user.mention if user else f"User {winner['user_id']}"
                    winners_text += (
                        f"{username}: {format_bits(winner['bet_amount'])} bet → "
                        f"{format_bits(winner['payout'])} won\n"
                    )
                
                if len(winners_info) > 10:
                    winners_text += f"\n... and {len(winners_info) - 10} more winner(s)"
                
                if winners_text:
                    embed.add_field(
                        name="🎯 Winners",
                        value=winners_text,
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                await session.rollback()
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"❌ Error resolving wager: {str(e)}",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"❌ Error resolving wager: {str(e)}",
                        ephemeral=True
                    )
    
    @app_commands.command(name="admin", description="Admin commands")
    async def admin(self, interaction: discord.Interaction):
        """Admin command group placeholder."""
        await interaction.response.send_message(
            "Use `/admin balance` or `/admin close` for admin actions.",
            ephemeral=True
        )
    
    @app_commands.command(name="admin_balance", description="Adjust a user's balance (Admin only)")
    @app_commands.describe(
        user="The user whose balance to adjust",
        amount="The amount to add (positive) or subtract (negative)"
    )
    async def admin_balance(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        amount: int
    ):
        """Adjust a user's balance."""
        if not is_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        if amount == 0:
            await interaction.response.send_message(
                "❌ Amount cannot be zero.",
                ephemeral=True
            )
            return
        
        async with get_session() as session:
            try:
                target_user = await get_user(session, user.id)
                old_balance = target_user.bits_balance
                
                new_balance = await update_balance(
                    session,
                    user.id,
                    amount,
                    TRANSACTION_TYPE_ADMIN_ADJUSTMENT,
                    reference_id=None
                )
                
                embed = discord.Embed(
                    title="💰 Balance Adjusted",
                    color=discord.Color.green() if amount > 0 else discord.Color.red()
                )
                embed.add_field(name="User", value=user.mention, inline=False)
                embed.add_field(name="Change", value=f"{'+' if amount > 0 else ''}{format_bits(amount)}", inline=True)
                embed.add_field(name="Old Balance", value=format_bits(old_balance), inline=True)
                embed.add_field(name="New Balance", value=format_bits(new_balance), inline=True)
                embed.set_footer(text=f"Adjusted by {interaction.user.name}")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Error adjusting balance: {str(e)}",
                    ephemeral=True
                )
    
    @app_commands.command(name="admin_close", description="Close a wager to prevent new bets (Admin only)")
    @app_commands.describe(wager_id="The ID of the wager to close")
    async def admin_close(self, interaction: discord.Interaction, wager_id: int):
        """Close a wager to prevent new bets."""
        if not is_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        async with get_session() as session:
            try:
                result = await session.execute(
                    select(Wager).where(Wager.wager_id == wager_id)
                )
                wager = result.scalar_one_or_none()
                
                if not wager:
                    await interaction.response.send_message(
                        f"❌ Wager with ID {wager_id} not found.",
                        ephemeral=True
                    )
                    return
                
                if wager.status != WAGER_STATUS_OPEN:
                    await interaction.response.send_message(
                        f"❌ This wager is already {wager.status}.",
                        ephemeral=True
                    )
                    return
                
                wager.status = WAGER_STATUS_CLOSED
                await session.commit()
                
                # Update pinned message if it exists
                await update_wager_message(self.bot, wager_id)
                
                embed = discord.Embed(
                    title="🔒 Wager Closed",
                    description=f"**{wager.title}**\n\nThis wager is now closed. No new bets can be placed.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await session.rollback()
                await interaction.response.send_message(
                    f"❌ Error closing wager: {str(e)}",
                    ephemeral=True
                )
    
    @app_commands.command(name="set_wager_channel", description="View or set the wager channel (Admin only)")
    @app_commands.describe(channel="The channel where wagers will be posted (optional - leave empty to view current)")
    async def set_wager_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        """View or set the wager channel."""
        if not is_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        if channel:
            # User wants to set a channel
            # Check permissions
            if not channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message(
                    f"❌ I don't have permission to send messages in {channel.mention}. Please grant 'Send Messages' permission.",
                    ephemeral=True
                )
                return
            
            if not channel.permissions_for(interaction.guild.me).manage_messages:
                await interaction.response.send_message(
                    f"❌ I don't have permission to pin messages in {channel.mention}. Please grant 'Manage Messages' permission.",
                    ephemeral=True
                )
                return
            
            # Store in database
            async with get_session() as session:
                try:
                    result = await session.execute(
                        select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id)
                    )
                    guild_settings = result.scalar_one_or_none()
                    
                    if not guild_settings:
                        guild_settings = GuildSettings(
                            guild_id=interaction.guild.id,
                            wager_channel_id=channel.id
                        )
                        session.add(guild_settings)
                    else:
                        guild_settings.wager_channel_id = channel.id
                    
                    await session.commit()
                    
                    embed = discord.Embed(
                        title="Wager Channel Configuration",
                        description=f"**Wager Channel Set**\n\nAll new wagers will be posted to {channel.mention}",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Channel ID",
                        value=f"`{channel.id}`",
                        inline=True
                    )
                    embed.add_field(
                        name="Channel Name",
                        value=channel.name,
                        inline=True
                    )
                    embed.add_field(
                        name="✅ Saved",
                        value="This setting has been saved to the database and will persist across bot restarts.",
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                except Exception as e:
                    await session.rollback()
                    await interaction.response.send_message(
                        f"❌ Error saving channel setting: {str(e)}",
                        ephemeral=True
                    )
        else:
            # User wants to view current channel
            async with get_session() as session:
                try:
                    # Check database first
                    result = await session.execute(
                        select(GuildSettings).where(GuildSettings.guild_id == interaction.guild.id)
                    )
                    guild_settings = result.scalar_one_or_none()
                    
                    current_channel = None
                    channel_source = None
                    
                    # Check database setting
                    if guild_settings and guild_settings.wager_channel_id:
                        current_channel = self.bot.get_channel(guild_settings.wager_channel_id)
                        if current_channel and current_channel.guild.id == interaction.guild.id:
                            channel_source = "database"
                    
                    # Check environment variable if database doesn't have it
                    if not current_channel and config.WAGER_CHANNEL_ID:
                        env_channel = self.bot.get_channel(config.WAGER_CHANNEL_ID)
                        if env_channel and env_channel.guild.id == interaction.guild.id:
                            current_channel = env_channel
                            channel_source = "environment"
                    
                    if current_channel:
                        embed = discord.Embed(
                            title="Wager Channel Configuration",
                            description=f"**Current Wager Channel:** {current_channel.mention}",
                            color=discord.Color.blue()
                        )
                        embed.add_field(
                            name="Channel ID",
                            value=f"`{current_channel.id}`",
                            inline=True
                        )
                        embed.add_field(
                            name="Channel Name",
                            value=current_channel.name,
                            inline=True
                        )
                        embed.add_field(
                            name="Source",
                            value="Database (per-guild)" if channel_source == "database" else "Environment Variable (global)",
                            inline=True
                        )
                        # Check permissions
                        perms_ok = (
                            current_channel.permissions_for(interaction.guild.me).send_messages and
                            current_channel.permissions_for(interaction.guild.me).manage_messages
                        )
                        embed.add_field(
                            name="Permissions",
                            value="✅ All permissions OK" if perms_ok else "❌ Missing required permissions",
                            inline=False
                        )
                    else:
                        embed = discord.Embed(
                            title="Wager Channel Configuration",
                            description="**No Channel Configured**\n\nWager channel is not set. The bot will automatically create or find a channel when you create your first wager, or you can use `/set_wager_channel <channel>` to set one manually.",
                            color=discord.Color.orange()
                        )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                except Exception as e:
                    await interaction.response.send_message(
                        f"❌ Error retrieving channel setting: {str(e)}",
                        ephemeral=True
                    )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(AdminCog(bot))

