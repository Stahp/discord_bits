"""Wager management cog for Discord Bits Wagering Bot."""
import discord
from discord.ext import commands
from discord import app_commands
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src import config
import logging
from src.database.database import get_session, get_user
from src.database.models import Wager, WAGER_STATUS_OPEN, GuildSettings
from src.utils.validators import validate_wager_title, validate_wager_options
from src.utils.formatters import format_wager_embed, format_bits
from src.cogs.betting import WagerOptionView, update_wager_message

logger = logging.getLogger(__name__)


async def get_or_create_wager_channel(bot: commands.Bot, guild: discord.Guild, session) -> discord.TextChannel:
    """Get or create the wager channel for a guild."""
    from database.models import GuildSettings
    
    # First check environment variable (global setting)
    if config.WAGER_CHANNEL_ID:
        channel = bot.get_channel(config.WAGER_CHANNEL_ID)
        if channel and channel.guild.id == guild.id:
            return channel
    
    # Check database for guild-specific setting
    result = await session.execute(
        select(GuildSettings).where(GuildSettings.guild_id == guild.id)
    )
    guild_settings = result.scalar_one_or_none()
    
    if guild_settings and guild_settings.wager_channel_id:
        channel = bot.get_channel(guild_settings.wager_channel_id)
        if channel and channel.guild.id == guild.id:
            return channel
    
    # Try to find existing channel with common names
    channel_names = ["wagers", "betting", "bets", "wager-bot"]
    for channel_name in channel_names:
        for channel in guild.text_channels:
            if channel.name.lower() == channel_name.lower():
                # Check permissions
                if (channel.permissions_for(guild.me).send_messages and 
                    channel.permissions_for(guild.me).manage_messages):
                    # Store it in database
                    if not guild_settings:
                        guild_settings = GuildSettings(guild_id=guild.id, wager_channel_id=channel.id)
                        session.add(guild_settings)
                    else:
                        guild_settings.wager_channel_id = channel.id
                    await session.commit()
                    return channel
    
    # Create a new channel
    try:
        # Check if bot has permission to create channels
        if not guild.me.guild_permissions.manage_channels:
            raise PermissionError("Bot doesn't have permission to create channels")
        
        # Create the channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False,  # Only bot can send messages
                add_reactions=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True  # manage_messages includes pinning
            )
        }
        
        channel = await guild.create_text_channel(
            "wagers",
            overwrites=overwrites,
            topic="Wager messages are automatically posted and pinned here. Click the buttons to place bets!"
        )
        
        # Store in database
        if not guild_settings:
            guild_settings = GuildSettings(guild_id=guild.id, wager_channel_id=channel.id)
            session.add(guild_settings)
        else:
            guild_settings.wager_channel_id = channel.id
        await session.commit()
        
        logger.info(f"Created wager channel {channel.id} for guild {guild.id}")
        return channel
        
    except Exception as e:
        logger.error(f"Failed to create wager channel: {e}")
        raise


class CreateWagerModal(discord.ui.Modal, title="Create New Wager"):
    """Modal for creating a new wager."""
    
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
    
    title_input = discord.ui.TextInput(
        label="Title",
        placeholder="e.g., Who will win the game?",
        required=True,
        max_length=256
    )
    
    description_input = discord.ui.TextInput(
        label="Description",
        placeholder="Optional details about the wager",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=4000
    )
    
    options_input = discord.ui.TextInput(
        label="Options",
        placeholder="Option 1, Option 2, Option 3 (comma-separated, 2-10 options)",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=4000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        # Parse options
        option_list = [opt.strip() for opt in self.options_input.value.split(",") if opt.strip()]
        
        # Validate title
        is_valid, error_msg = validate_wager_title(self.title_input.value)
        if not is_valid:
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
            return
        
        # Validate options
        is_valid, error_msg = validate_wager_options(option_list)
        if not is_valid:
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
            return
        
        async with get_session() as session:
            try:
                # Ensure user exists
                user = await get_user(session, interaction.user.id)
                
                # Get or create wager channel
                try:
                    target_channel = await get_or_create_wager_channel(self.bot, interaction.guild, session)
                except PermissionError as e:
                    await interaction.response.send_message(
                        f"❌ {str(e)}. Please grant 'Manage Channels' permission or use `/set_wager_channel` to set an existing channel.",
                        ephemeral=True
                    )
                    return
                except Exception as e:
                    logger.error(f"Error getting/creating wager channel: {e}", exc_info=True)
                    await interaction.response.send_message(
                        f"❌ Failed to get or create wager channel: {str(e)}",
                        ephemeral=True
                    )
                    return
                
                # Verify permissions
                if not target_channel.permissions_for(interaction.guild.me).send_messages:
                    await interaction.response.send_message(
                        f"❌ I don't have permission to send messages in {target_channel.mention}. Please grant 'Send Messages' permission.",
                        ephemeral=True
                    )
                    return
                
                if not target_channel.permissions_for(interaction.guild.me).manage_messages:
                    await interaction.response.send_message(
                        f"❌ I don't have permission to pin messages in {target_channel.mention}. Please grant 'Manage Messages' permission.",
                        ephemeral=True
                    )
                    return
                
                # Create wager
                wager = Wager(
                    creator_id=interaction.user.id,
                    title=self.title_input.value,
                    description=self.description_input.value if self.description_input.value else None,
                    options=option_list,
                    status=WAGER_STATUS_OPEN
                )
                session.add(wager)
                await session.commit()
                await session.refresh(wager)
                
                # Create embed
                embed = format_wager_embed(wager, bets_by_option=None, show_stats=True)
                
                # Create view with buttons
                view = WagerOptionView(wager.wager_id, wager.options, self.bot)
                
                # Post message to channel
                try:
                    message = await target_channel.send(embed=embed, view=view)
                    
                    # Pin the message
                    try:
                        await message.pin()
                    except discord.HTTPException as e:
                        logger.warning(f"Could not pin message {message.id}: {e}")
                        # Continue even if pinning fails
                    
                    # Store message and channel IDs
                    wager.message_id = message.id
                    wager.channel_id = target_channel.id
                    await session.commit()
                    
                    # Register the view as persistent
                    self.bot.add_view(view, message_id=message.id)
                    
                    await interaction.response.send_message(
                        f"✅ Wager created and pinned in {target_channel.mention}!",
                        ephemeral=True
                    )
                    
                except discord.HTTPException as e:
                    logger.error(f"Error posting wager message: {e}")
                    await interaction.response.send_message(
                        f"❌ Error posting wager message: {str(e)}",
                        ephemeral=True
                    )
                    # Delete the wager if message posting failed
                    await session.delete(wager)
                    await session.commit()
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating wager: {e}", exc_info=True)
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"❌ Error creating wager: {str(e)}",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"❌ Error creating wager: {str(e)}",
                        ephemeral=True
                    )


class WagersCog(commands.Cog):
    """Cog for managing wagers."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="createwager", description="Create a new wager")
    async def createwager(self, interaction: discord.Interaction):
        """Create a new wager using a modal."""
        modal = CreateWagerModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="wagers", description="List all active wagers")
    async def wagers(self, interaction: discord.Interaction):
        """List all active wagers."""
        async with get_session() as session:
            try:
                # Get all open wagers
                result = await session.execute(
                    select(Wager)
                    .where(Wager.status == WAGER_STATUS_OPEN)
                    .order_by(Wager.created_at.desc())
                    .limit(20)
                )
                wagers_list = result.scalars().all()
                
                if not wagers_list:
                    await interaction.response.send_message(
                        "📭 No active wagers found. Create one with `/createwager`!",
                        ephemeral=True
                    )
                    return
                
                embed = discord.Embed(
                    title="🎲 Active Wagers",
                    color=discord.Color.blue()
                )
                
                wager_list_text = ""
                for wager in wagers_list:
                    wager_list_text += f"**{wager.wager_id}.** {wager.title}\n"
                
                embed.description = wager_list_text
                embed.set_footer(text=f"Showing {len(wagers_list)} active wager(s). Use /wagerinfo <id> for details.")
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Error retrieving wagers: {str(e)}",
                    ephemeral=True
                )
    
    @app_commands.command(name="wagerinfo", description="View details of a specific wager")
    @app_commands.describe(wager_id="The ID of the wager to view")
    async def wagerinfo(self, interaction: discord.Interaction, wager_id: int):
        """View details of a specific wager."""
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
                
                # Organize bets by option
                bets_by_option = {}
                for bet in wager.bets:
                    if bet.option_index not in bets_by_option:
                        bets_by_option[bet.option_index] = []
                    bets_by_option[bet.option_index].append(bet)
                
                embed = format_wager_embed(wager, bets_by_option)
                
                # Add total pool information
                total_pool = sum(bet.amount for bet in wager.bets)
                if total_pool > 0:
                    embed.add_field(
                        name="💰 Total Pool",
                        value=format_bits(total_pool),
                        inline=True
                    )
                    embed.add_field(
                        name="📊 Total Bets",
                        value=str(len(wager.bets)),
                        inline=True
                    )
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Error retrieving wager: {str(e)}",
                    ephemeral=True
                )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(WagersCog(bot))

