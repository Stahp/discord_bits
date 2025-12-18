"""Help cog for Discord Bits Wagering Bot."""
import discord
from discord.ext import commands
from discord import app_commands


class HelpCog(commands.Cog):
    """Cog for help commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="help", description="Show help information about the bot")
    async def help(self, interaction: discord.Interaction):
        """Show help information."""
        embed = discord.Embed(
            title="🎲 Discord Bits Wagering Bot - Help",
            description="A bot that allows users to create and participate in wagers using bits!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💰 Balance Commands",
            value=(
                "`/balance` - Check your bits balance\n"
                "`/daily` - Claim your daily reward (100 bits)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎲 Wager Commands",
            value=(
                "`/createwager` - Create a new wager\n"
                "`/wagers` - List all active wagers\n"
                "`/wagerinfo <id>` - View details of a specific wager"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎯 Betting Commands",
            value=(
                "`/bet <wager_id> <option> <amount>` - Place a bet on a wager\n"
                "`/mybets` - View your active bets"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Admin Commands",
            value=(
                "`/resolve <wager_id> <winning_option>` - Resolve a wager (Admin only)\n"
                "`/admin_balance <user> <amount>` - Adjust user balance (Admin only)\n"
                "`/admin_close <wager_id>` - Close a wager (Admin only)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📖 How It Works",
            value=(
                "1. Use `/daily` to claim your daily reward and get bits\n"
                "2. Create wagers with `/createwager` or bet on existing ones with `/bet`\n"
                "3. When a wager is resolved, winners get their share of the total pool\n"
                "4. New users start with 1000 bits!"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use /help for more information")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(HelpCog(bot))

