"""Message formatting helpers."""
import discord
from datetime import datetime


def format_bits(amount: int) -> str:
    """Format bits amount with commas."""
    return f"{amount:,} bits"


def format_wager_embed(wager, bets_by_option=None, show_stats=True) -> discord.Embed:
    """Format a wager as an embed with live betting statistics."""
    from database.models import WAGER_STATUS_OPEN, WAGER_STATUS_RESOLVED
    
    embed = discord.Embed(
        title=f"🎲 {wager.title}",
        description=wager.description or "No description provided.",
        color=discord.Color.blue() if wager.status == WAGER_STATUS_OPEN else discord.Color.greyple()
    )
    
    embed.add_field(name="Wager ID", value=f"`{wager.wager_id}`", inline=True)
    embed.add_field(name="Status", value=wager.status.upper(), inline=True)
    embed.add_field(name="Created", value=f"<t:{int(wager.created_at.timestamp())}:R>", inline=True)
    
    # Calculate statistics if bets are provided
    total_pool = 0
    total_bets_count = 0
    if bets_by_option:
        for bets in bets_by_option.values():
            total_pool += sum(bet.amount for bet in bets)
            total_bets_count += len(bets)
    
    # Add options with betting statistics
    options_text = ""
    for idx, option in enumerate(wager.options):
        option_label = f"**{idx + 1}.** {option}"
        if bets_by_option:
            option_bets = bets_by_option.get(idx, [])
            option_total = sum(bet.amount for bet in option_bets)
            option_count = len(option_bets)
            
            if option_total > 0:
                # Calculate percentage of total pool
                percentage = (option_total / total_pool * 100) if total_pool > 0 else 0
                option_label += f"\n   💰 {format_bits(option_total)} ({percentage:.1f}%) • 👥 {option_count} bet{'s' if option_count != 1 else ''}"
            else:
                option_label += "\n   💰 No bets yet"
        options_text += option_label + "\n\n"
    
    embed.add_field(name="Options", value=options_text or "No options", inline=False)
    
    # Add live statistics if available
    if show_stats and bets_by_option and total_pool > 0:
        embed.add_field(
            name="💰 Total Pool",
            value=format_bits(total_pool),
            inline=True
        )
        embed.add_field(
            name="📊 Total Bets",
            value=str(total_bets_count),
            inline=True
        )
    
    if wager.status == WAGER_STATUS_RESOLVED and wager.winning_option is not None:
        embed.add_field(
            name="🏆 Winner",
            value=f"Option {wager.winning_option + 1}: {wager.options[wager.winning_option]}",
            inline=False
        )
        embed.color = discord.Color.gold()
    
    embed.set_footer(text=f"Created by {wager.creator_id}")
    
    return embed


def format_balance_embed(user, balance: int) -> discord.Embed:
    """Format user balance as an embed."""
    embed = discord.Embed(
        title="💰 Your Bits Balance",
        color=discord.Color.green()
    )
    embed.add_field(name="Balance", value=format_bits(balance), inline=False)
    embed.set_footer(text=f"User ID: {user.user_id}")
    return embed


def format_bet_embed(bet, wager) -> discord.Embed:
    """Format a bet as an embed."""
    embed = discord.Embed(
        title="🎯 Bet Placed",
        color=discord.Color.blue()
    )
    embed.add_field(name="Wager", value=wager.title, inline=False)
    embed.add_field(name="Option", value=f"Option {bet.option_index + 1}: {wager.options[bet.option_index]}", inline=False)
    embed.add_field(name="Amount", value=format_bits(bet.amount), inline=False)
    embed.set_footer(text=f"Bet ID: {bet.bet_id}")
    return embed

