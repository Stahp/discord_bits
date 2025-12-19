"""Betting cog for Discord Bits Wagering Bot."""
import discord
from discord.ext import commands
from discord import app_commands
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src import config
import logging
from src.database.database import get_session, get_user, update_balance
from src.database.models import (
    Wager, Bet, WAGER_STATUS_OPEN, WAGER_STATUS_RESOLVED,
    TRANSACTION_TYPE_BET_PLACED, TRANSACTION_TYPE_BET_WON, TRANSACTION_TYPE_BET_REFUNDED
)
from src.utils.validators import validate_bet_amount
from src.utils.formatters import format_bet_embed, format_bits, format_wager_embed

logger = logging.getLogger(__name__)


class BetAmountModal(discord.ui.Modal, title="Place Your Bet"):
    """Modal for entering bet amount."""
    
    def __init__(self, wager_id: int, option_index: int, bot: commands.Bot):
        super().__init__()
        self.wager_id = wager_id
        self.option_index = option_index
        self.bot = bot
    
    amount = discord.ui.TextInput(
        label="Bet Amount",
        placeholder="Enter amount in bits (minimum 10)",
        required=True,
        min_length=1,
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        try:
            amount = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid amount. Please enter a number.",
                ephemeral=True
            )
            return
        
        # Validate bet amount
        is_valid, error_msg = validate_bet_amount(amount)
        if not is_valid:
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
            return
        
        # Place the bet
        async with get_session() as session:
            try:
                # Get wager
                result = await session.execute(
                    select(Wager)
                    .where(Wager.wager_id == self.wager_id)
                )
                wager = result.scalar_one_or_none()
                
                if not wager:
                    await interaction.response.send_message(
                        f"❌ Wager not found.",
                        ephemeral=True
                    )
                    return
                
                # Check wager status
                if wager.status != WAGER_STATUS_OPEN:
                    await interaction.response.send_message(
                        f"❌ This wager is {wager.status}. You cannot place bets on it.",
                        ephemeral=True
                    )
                    return
                
                # Get user and check balance
                user = await get_user(session, interaction.user.id)
                if user.bits_balance < amount:
                    await interaction.response.send_message(
                        f"❌ Insufficient balance. You have {format_bits(user.bits_balance)}, but need {format_bits(amount)}.",
                        ephemeral=True
                    )
                    return
                
                # Check if user already bet on this wager
                existing_bet_result = await session.execute(
                    select(Bet)
                    .where(Bet.wager_id == self.wager_id)
                    .where(Bet.user_id == interaction.user.id)
                )
                existing_bet = existing_bet_result.scalar_one_or_none()
                
                if existing_bet:
                    await interaction.response.send_message(
                        f"❌ You've already placed a bet on this wager (Option {existing_bet.option_index + 1}, {format_bits(existing_bet.amount)}).",
                        ephemeral=True
                    )
                    return
                
                # Deduct balance
                await update_balance(
                    session,
                    interaction.user.id,
                    -amount,
                    TRANSACTION_TYPE_BET_PLACED,
                    reference_id=None
                )
                
                # Create bet
                bet = Bet(
                    wager_id=self.wager_id,
                    user_id=interaction.user.id,
                    option_index=self.option_index,
                    amount=amount
                )
                session.add(bet)
                await session.commit()
                await session.refresh(bet)
                
                # Update transaction reference
                from database.models import Transaction
                transaction_result = await session.execute(
                    select(Transaction)
                    .where(Transaction.user_id == interaction.user.id)
                    .where(Transaction.transaction_type == TRANSACTION_TYPE_BET_PLACED)
                    .order_by(Transaction.created_at.desc())
                    .limit(1)
                )
                transaction = transaction_result.scalar_one()
                transaction.reference_id = bet.bet_id
                await session.commit()
                
                # Get updated balance
                user = await get_user(session, interaction.user.id)
                
                # Update pinned message if it exists
                await update_wager_message(self.bot, self.wager_id)
                
                embed = format_bet_embed(bet, wager)
                embed.add_field(
                    name="New Balance",
                    value=format_bits(user.bits_balance),
                    inline=False
                )
                await interaction.response.send_message(
                    f"✅ Bet placed successfully!",
                    embed=embed,
                    ephemeral=True
                )
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error placing bet: {e}", exc_info=True)
                await interaction.response.send_message(
                    f"❌ Error placing bet: {str(e)}",
                    ephemeral=True
                )


class WagerOptionView(discord.ui.View):
    """Persistent view for wager option buttons."""
    
    def __init__(self, wager_id: int, options: list, bot: commands.Bot):
        super().__init__(timeout=None)
        self.wager_id = wager_id
        self.options = options
        self.bot = bot
        
        # Create a button for each option
        for idx, option in enumerate(options):
            # Truncate option text if too long (Discord button label limit is 80 chars)
            button_label = option[:77] + "..." if len(option) > 80 else option
            button = discord.ui.Button(
                label=button_label,
                style=discord.ButtonStyle.primary,
                custom_id=f"wager_{wager_id}_option_{idx}"
            )
            button.callback = self.create_option_callback(idx)
            self.add_item(button)
    
    def create_option_callback(self, option_index: int):
        """Create a callback function for an option button."""
        async def callback(interaction: discord.Interaction):
            # Check if wager is still open
            async with get_session() as session:
                result = await session.execute(
                    select(Wager)
                    .where(Wager.wager_id == self.wager_id)
                )
                wager = result.scalar_one_or_none()
                
                if not wager:
                    await interaction.response.send_message(
                        "❌ This wager no longer exists.",
                        ephemeral=True
                    )
                    return
                
                if wager.status != WAGER_STATUS_OPEN:
                    await interaction.response.send_message(
                        f"❌ This wager is {wager.status}. You cannot place bets on it.",
                        ephemeral=True
                    )
                    return
                
                # Show modal for bet amount
                modal = BetAmountModal(self.wager_id, option_index, self.bot)
                await interaction.response.send_modal(modal)
        
        return callback


async def update_wager_message(bot: commands.Bot, wager_id: int):
    """Update the pinned wager message with latest betting statistics."""
    async with get_session() as session:
        try:
            # Get wager with bets
            result = await session.execute(
                select(Wager)
                .options(selectinload(Wager.bets))
                .where(Wager.wager_id == wager_id)
            )
            wager = result.scalar_one_or_none()
            
            if not wager or not wager.message_id or not wager.channel_id:
                return  # No pinned message to update
            
            # Get channel and message
            channel = bot.get_channel(wager.channel_id)
            if not channel:
                logger.warning(f"Channel {wager.channel_id} not found for wager {wager_id}")
                return
            
            try:
                message = await channel.fetch_message(wager.message_id)
            except discord.NotFound:
                logger.warning(f"Message {wager.message_id} not found for wager {wager_id}")
                # Clear message_id from database
                wager.message_id = None
                wager.channel_id = None
                await session.commit()
                return
            except discord.Forbidden:
                logger.warning(f"No permission to fetch message {wager.message_id} for wager {wager_id}")
                return
            
            # Organize bets by option
            bets_by_option = {}
            for bet in wager.bets:
                if bet.option_index not in bets_by_option:
                    bets_by_option[bet.option_index] = []
                bets_by_option[bet.option_index].append(bet)
            
            # Create updated embed
            embed = format_wager_embed(wager, bets_by_option, show_stats=True)
            
            # Create view with buttons (always create, but disable if closed/resolved)
            view = WagerOptionView(wager.wager_id, wager.options, bot)
            if wager.status != WAGER_STATUS_OPEN:
                # Disable all buttons if wager is not open
                for item in view.children:
                    item.disabled = True
            
            # Update message
            await message.edit(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error updating wager message {wager_id}: {e}", exc_info=True)


class BettingCog(commands.Cog):
    """Cog for placing bets on wagers."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="bet", description="Place a bet on a wager")
    @app_commands.describe(
        wager_id="The ID of the wager to bet on",
        option="The option number to bet on (1-based index)",
        amount="The amount of bits to bet"
    )
    async def bet(
        self,
        interaction: discord.Interaction,
        wager_id: int,
        option: int,
        amount: int
    ):
        """Place a bet on a wager."""
        # Validate bet amount
        is_valid, error_msg = validate_bet_amount(amount)
        if not is_valid:
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
            return
        
        # Validate option (convert to 0-based index)
        option_index = option - 1
        if option_index < 0:
            await interaction.response.send_message(
                "❌ Option number must be at least 1.",
                ephemeral=True
            )
            return
        
        async with get_session() as session:
            try:
                # Get wager
                result = await session.execute(
                    select(Wager)
                    .where(Wager.wager_id == wager_id)
                )
                wager = result.scalar_one_or_none()
                
                if not wager:
                    await interaction.response.send_message(
                        f"❌ Wager with ID {wager_id} not found.",
                        ephemeral=True
                    )
                    return
                
                # Check wager status
                if wager.status != WAGER_STATUS_OPEN:
                    await interaction.response.send_message(
                        f"❌ This wager is {wager.status}. You cannot place bets on it.",
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
                
                # Get user and check balance
                user = await get_user(session, interaction.user.id)
                if user.bits_balance < amount:
                    await interaction.response.send_message(
                        f"❌ Insufficient balance. You have {format_bits(user.bits_balance)}, but need {format_bits(amount)}.",
                        ephemeral=True
                    )
                    return
                
                # Check if user already bet on this wager
                existing_bet_result = await session.execute(
                    select(Bet)
                    .where(Bet.wager_id == wager_id)
                    .where(Bet.user_id == interaction.user.id)
                )
                existing_bet = existing_bet_result.scalar_one_or_none()
                
                if existing_bet:
                    await interaction.response.send_message(
                        f"❌ You've already placed a bet on this wager (Option {existing_bet.option_index + 1}, {format_bits(existing_bet.amount)}).",
                        ephemeral=True
                    )
                    return
                
                # Deduct balance
                await update_balance(
                    session,
                    interaction.user.id,
                    -amount,
                    TRANSACTION_TYPE_BET_PLACED,
                    reference_id=None  # Will be updated after bet is created
                )
                
                # Create bet
                bet = Bet(
                    wager_id=wager_id,
                    user_id=interaction.user.id,
                    option_index=option_index,
                    amount=amount
                )
                session.add(bet)
                await session.commit()
                await session.refresh(bet)
                
                # Update transaction reference
                from database.models import Transaction
                transaction_result = await session.execute(
                    select(Transaction)
                    .where(Transaction.user_id == interaction.user.id)
                    .where(Transaction.transaction_type == TRANSACTION_TYPE_BET_PLACED)
                    .order_by(Transaction.created_at.desc())
                    .limit(1)
                )
                transaction = transaction_result.scalar_one()
                transaction.reference_id = bet.bet_id
                await session.commit()
                
                # Get updated balance
                user = await get_user(session, interaction.user.id)
                
                # Update pinned message if it exists
                await update_wager_message(self.bot, wager_id)
                
                embed = format_bet_embed(bet, wager)
                embed.add_field(
                    name="New Balance",
                    value=format_bits(user.bits_balance),
                    inline=False
                )
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                await session.rollback()
                await interaction.response.send_message(
                    f"❌ Error placing bet: {str(e)}",
                    ephemeral=True
                )
    
    @app_commands.command(name="mybets", description="View your active bets")
    async def mybets(self, interaction: discord.Interaction):
        """View user's active bets."""
        async with get_session() as session:
            try:
                # Get all bets for user on open wagers
                result = await session.execute(
                    select(Bet)
                    .join(Wager)
                    .where(Bet.user_id == interaction.user.id)
                    .where(Wager.status == WAGER_STATUS_OPEN)
                    .options(selectinload(Bet.wager))
                    .order_by(Bet.created_at.desc())
                )
                bets = result.scalars().all()
                
                if not bets:
                    await interaction.response.send_message(
                        "📭 You don't have any active bets. Use `/wagers` to see available wagers!",
                        ephemeral=True
                    )
                    return
                
                embed = discord.Embed(
                    title="🎯 Your Active Bets",
                    color=discord.Color.blue()
                )
                
                bets_text = ""
                total_bet = 0
                for bet in bets:
                    wager = bet.wager
                    option_text = wager.options[bet.option_index]
                    bets_text += (
                        f"**Wager #{wager.wager_id}:** {wager.title}\n"
                        f"Option {bet.option_index + 1}: {option_text} - {format_bits(bet.amount)}\n\n"
                    )
                    total_bet += bet.amount
                
                embed.description = bets_text
                embed.add_field(
                    name="💰 Total Bet",
                    value=format_bits(total_bet),
                    inline=False
                )
                embed.set_footer(text=f"You have {len(bets)} active bet(s)")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Error retrieving bets: {str(e)}",
                    ephemeral=True
                )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(BettingCog(bot))

