from discord.ext import commands
from discord import Embed
import discord
from typing import Optional
from storage import GameStorage
from constants import MESSAGES, COMMANDS
import re

class GamingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.storage = GameStorage()
        # Remove default help command
        self.bot.remove_command('help')

    def get_backloggd_url(self, game_name: str) -> str:
        """Generate a Backloggd search URL for the game"""
        # Convert to lowercase and replace spaces with hyphens
        formatted_name = game_name.lower()
        # Remove special characters except hyphens
        formatted_name = re.sub(r'[^a-z0-9\-]', '', formatted_name.replace(' ', '-'))
        return f"https://backloggd.com/games/{formatted_name}"

    @commands.command(name='log')
    async def log_hours(self, ctx, hours: Optional[str] = None, *, game: Optional[str] = None):
        """Log gaming hours and earn credits"""
        try:
            # Validate input
            if not hours or not game:
                await ctx.send(MESSAGES['invalid_game'])
                return

            try:
                hours_float = float(hours)
                if not 0.5 <= hours_float <= 24:
                    await ctx.send(MESSAGES['invalid_hours'])
                    return
            except ValueError:
                await ctx.send(MESSAGES['invalid_hours'])
                return

            # Get game info before logging
            game_info = self.storage.get_game_info(game)

            # Log hours and get earned credits
            credits = self.storage.add_gaming_hours(ctx.author.id, hours_float, game)

            # Generate Backloggd URL
            backloggd_url = self.get_backloggd_url(game)

            # Create detailed response
            if game_info:
                await ctx.send(
                    f"✅ Successfully logged {hours_float} hours for {game}!\n"
                    f"📊 Rate: {game_info['credits_per_hour']} cred/hour\n"
                    f"💎 You earned {credits:.1f} cred!\n"
                    f"🎮 View on Backloggd: {backloggd_url}"
                )
            else:
                await ctx.send(MESSAGES['success_log'].format(
                    hours=hours_float,
                    game=game,
                    credits=credits
                ) + f"\n🎮 View on Backloggd: {backloggd_url}")

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='setrate')
    async def set_game_rate(self, ctx, credits: Optional[str] = None, *, game: Optional[str] = None):
        """Set credits per hour for a game"""
        try:
            if not credits or not game:
                await ctx.send("❌ Please provide both credits per hour and game name (!setrate <credits> <game>)")
                return

            try:
                credits_float = float(credits)
                if not 0.1 <= credits_float <= 10.0:
                    await ctx.send("❌ Credits per hour must be between 0.1 and 10.0")
                    return
            except ValueError:
                await ctx.send("❌ Please provide a valid number for credits per hour")
                return

            if self.storage.set_game_credits_per_hour(game, credits_float, ctx.author.id):
                await ctx.send(f"✅ Set rate for {game} to {credits_float} cred/hour!")
            else:
                await ctx.send("❌ Failed to set game rate")

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='rate')
    async def get_game_rate(self, ctx, *, game: Optional[str] = None):
        """Get credits per hour for a game"""
        try:
            if not game:
                await ctx.send("❌ Please provide a game name (!rate <game>)")
                return

            game_info = self.storage.get_game_info(game)
            if game_info:
                await ctx.send(
                    f"📊 Rate for {game}: {game_info['credits_per_hour']} cred/hour\n"
                    f"👤 Set by: <@{game_info['added_by']}>"
                )
            else:
                await ctx.send(f"❓ Game '{game}' not found in database")

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='balance')
    async def check_balance(self, ctx):
        """Check personal gamer cred balance"""
        try:
            credits = self.storage.get_user_credits(ctx.author.id)
            if credits == 0:
                await ctx.send(MESSAGES['no_balance'])
            else:
                await ctx.send(MESSAGES['balance'].format(credits=credits))
        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='leaderboard')
    async def show_leaderboard(self, ctx):
        """Show the gamer cred leaderboard"""
        try:
            leaderboard = self.storage.get_leaderboard()

            if not leaderboard:
                await ctx.send(MESSAGES['no_data'])
                return

            embed = Embed(title="🏆 Gamer Cred Leaderboard", color=0x00ff00)

            for position, (user_id, credits) in enumerate(leaderboard[:10], 1):
                user = self.bot.get_user(user_id)
                username = user.name if user else f"User{user_id}"
                embed.add_field(
                    name=f"{position}. {username}",
                    value=f"{credits:.1f} cred",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='weekly')
    async def weekly_leaderboard(self, ctx):
        """Show the weekly gamer cred leaderboard"""
        try:
            leaderboard = self.storage.get_leaderboard_by_timeframe(days=7)

            if not leaderboard:
                await ctx.send(MESSAGES['no_data'])
                return

            embed = Embed(title="📅 Weekly Gamer Cred Leaderboard", color=0x00ff00)

            for position, (user_id, credits, games) in enumerate(leaderboard[:10], 1):
                user = self.bot.get_user(user_id)
                username = user.name if user else f"User{user_id}"
                embed.add_field(
                    name=f"{position}. {username}",
                    value=f"{credits:.1f} cred (🎮 {games} games)",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='monthly')
    async def monthly_leaderboard(self, ctx):
        """Show the monthly gamer cred leaderboard"""
        try:
            leaderboard = self.storage.get_leaderboard_by_timeframe(days=30)

            if not leaderboard:
                await ctx.send(MESSAGES['no_data'])
                return

            embed = Embed(title="📅 Monthly Gamer Cred Leaderboard", color=0x00ff00)

            for position, (user_id, credits, games) in enumerate(leaderboard[:10], 1):
                user = self.bot.get_user(user_id)
                username = user.name if user else f"User{user_id}"
                embed.add_field(
                    name=f"{position}. {username}",
                    value=f"{credits:.1f} cred (🎮 {games} games)",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='history')
    async def show_history(self, ctx):
        """Show your gaming history"""
        try:
            history = self.storage.get_user_gaming_history(ctx.author.id)

            if not history:
                await ctx.send("You haven't logged any gaming sessions yet!")
                return

            embed = Embed(title=f"🎮 Gaming History for {ctx.author.name}", color=0x0088ff)

            for session in history:
                embed.add_field(
                    name=f"{session['game']} ({session['timestamp'].split('T')[0]})",
                    value=f"Hours: {session['hours']}\nCredits: {session['credits_earned']:.1f}\nRate: {session['rate']} cred/hour",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='achievements')
    async def show_achievements(self, ctx):
        """Show your gaming achievements"""
        try:
            achievements = self.storage.get_user_achievements(ctx.author.id)

            embed = Embed(title=f"🏆 Achievements for {ctx.author.name}", color=0xffd700)

            achievement_descriptions = {
                'novice_gamer': ('🎮 Novice Gamer', 'Play for 10+ hours'),
                'veteran_gamer': ('🎮🎮 Veteran Gamer', 'Play for 100+ hours'),
                'gaming_legend': ('🎮🎮🎮 Gaming Legend', 'Play for 1000+ hours'),
                'credit_collector': ('💎 Credit Collector', 'Earn 100+ credits'),
                'credit_hoarder': ('💎💎 Credit Hoarder', 'Earn 1000+ credits'),
                'game_explorer': ('🔍 Game Explorer', 'Play 5+ different games'),
                'game_connoisseur': ('🎯 Game Connoisseur', 'Play 20+ different games')
            }

            for achievement, (title, description) in achievement_descriptions.items():
                status = "✅" if achievements[achievement] else "❌"
                embed.add_field(
                    name=f"{status} {title}",
                    value=description,
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='help')
    async def show_help(self, ctx):
        """Show help message with available commands"""
        embed = Embed(title="📖 Gamer Cred Bot Commands", color=0x0088ff)

        # Update command descriptions
        commands_with_descriptions = {
            'log': '!log <hours> <game> - Log your gaming hours',
            'setrate': '!setrate <credits> <game> - Set credits per hour for a game (0.1-10.0)',
            'rate': '!rate <game> - Check credits per hour for a game',
            'balance': '!balance - Check your gamer cred balance',
            'leaderboard': '!leaderboard - View the gamer cred leaderboard',
            'weekly': '!weekly - View the weekly gamer cred leaderboard',
            'monthly': '!monthly - View the monthly gamer cred leaderboard',
            'history': '!history - View your gaming history',
            'achievements': '!achievements - View your achievements',
            'help': '!help - Show this help message'
        }

        for command, description in commands_with_descriptions.items():
            embed.add_field(name=command, value=description, inline=False)

        await ctx.send(embed=embed)