from discord.ext import commands
from discord import Embed
import discord
from typing import Optional
from storage import GameStorage
from constants import MESSAGES, COMMANDS, CHANNEL_ID
from models import LeaderboardPeriod, LeaderboardType
import re
import asyncio
import pytz
from discord.ext import tasks
from datetime import datetime, timedelta
import urllib.parse

class GamingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Remove default help command first
        if bot.help_command:
            bot.remove_command('help')
        
        # Initialize storage
        self.storage = GameStorage()
        print('Commands initialized successfully!')

    async def cog_check(self, ctx):
        """Check if the command is being used in the correct channel"""
        if CHANNEL_ID and ctx.channel.id != CHANNEL_ID:
            await ctx.send(MESSAGES['wrong_channel'])
            return False
        return True

    def get_ordinal_suffix(self, number: int) -> str:
        """Return the ordinal suffix for a number (1st, 2nd, 3rd, 4th, etc.)"""
        if 10 <= number % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
        return f"{number}{suffix}"

    def format_cst_time(self, dt):
        """Convert datetime to CST string"""
        if dt.tzinfo is None:  # Make naive datetime UTC
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt.astimezone(self.storage.cst).strftime('%Y-%m-%d %H:%M:%S %Z')

    @commands.command(name='log')
    async def log_hours(self, ctx, hours: float, *, game: str):
        """Log gaming hours"""
        try:
            # Validate hours
            if hours <= 0:
                await ctx.send("Hours must be greater than 0!")
                return

            # Add gaming hours
            credits_earned = await self.storage.add_gaming_hours(ctx.author.id, hours, game)

            # Get game info for the response
            game_info = self.storage.get_game_info(game)
            if not game_info:
                await ctx.send(f"Error: Could not find game '{game}'")
                return

            # URL encode the game name
            encoded_game = urllib.parse.quote(game_info['name'])

            # Send success message with original format
            await ctx.send(
                f"✅ Successfully logged {hours:,.1f} hours for {game_info['name']}!\n"
                f"📊 Rate: {game_info['credits_per_hour']:,.1f} cred/hour\n"
                f"💎 Earned {credits_earned:,.1f} cred!\n"
                f"🎮 View on Backloggd: {game_info['backloggd_url']}\n"
                f"🌐 View on [Gamer Cred](https://gamercred.onrender.com/game.html?game={encoded_game})"
            )

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='setrate')
    async def set_game_credits_per_hour(self, ctx, credits: float, *, game: str):
        """Set credits per hour for a game"""
        try:
            # Validate credits
            if credits < 0.1:
                await ctx.send("Credits per hour must be at least 0.1!\n🌐 View on [Gamer Cred](https://gamercred.onrender.com)")
                return

            # Set credits per hour
            success = await self.storage.set_game_credits_per_hour(game, credits, ctx.author.id)
            if success:
                # URL encode the game name
                encoded_game = urllib.parse.quote(game)
                
                await ctx.send(f"✅ Successfully set rate for {game} to {credits:,.1f} credits per hour!\n🌐 View on [Gamer Cred](https://gamercred.onrender.com/game.html?game={encoded_game})")
            else:
                await ctx.send(f"❌ Failed to set rate for {game}. Please try again.")
        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)) + "\n🌐 View on [Gamer Cred](https://gamercred.onrender.com)")

    @commands.command(name='rate')
    async def get_game_rate(self, ctx, *, game: Optional[str] = None):
        """Get credits per hour for a game"""
        try:
            if not game:
                await ctx.send("❌ Please provide a game name (!rate <game>)")
                return

            game_info = self.storage.get_game_info(game)
            if game_info:
                # Get the user who set the rate
                setter = None
                if game_info['added_by']:
                    setter = ctx.guild.get_member(int(game_info['added_by']))
                setter_name = setter.display_name if setter else f"Unknown User"

                # URL encode the game name
                encoded_game = urllib.parse.quote(game_info['name'])

                await ctx.send(
                    f"📊 Rate for {game}: {game_info['credits_per_hour']:,.1f} cred/hour\n"
                    f"👤 Set by: {setter_name}\n"
                    f"🎮 View the game on [Backloggd]({game_info['backloggd_url']})\n"
                    f"🌐 View on [Gamer Cred](https://gamercred.onrender.com/game.html?game={encoded_game})"
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
                await ctx.send(MESSAGES['balance'].format(credits=f"{credits:,.1f}") + "\n🌐 View on [Gamer Cred](https://gamercred.onrender.com)")
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
            embed.set_footer(text="🌐 View on Gamer Cred", icon_url="https://gamercred.onrender.com/favicon.ico")

            for position, (user_id, credits) in enumerate(leaderboard[:10], 1):
                member = ctx.guild.get_member(user_id)
                username = member.display_name if member else f"User{user_id}"
                embed.add_field(
                    name=f"{position}. {username}",
                    value=f"{credits:,.1f} cred",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='weekly')
    async def weekly_leaderboard(self, ctx):
        """Show the weekly gamer cred leaderboard"""
        try:
            # Get current period and leaderboard
            period = await self.storage.get_or_create_current_period(LeaderboardType.WEEKLY)
            leaderboard = await self.storage.get_leaderboard_by_timeframe(LeaderboardType.WEEKLY, self.bot, period=period)

            if not leaderboard:
                await ctx.send("No gaming activity in the current week!")
                return

            # Record the placements in history
            await self.storage.record_leaderboard_placements(LeaderboardType.WEEKLY, leaderboard, period)

            embed = Embed(
                title="📅 Weekly Gamer Cred Leaderboard",
                description=f"Period: {self.format_cst_time(period.start_time)} to {self.format_cst_time(period.end_time)}\nResets every Monday at 00:00 CST",
                color=0x00ff00,
                url="https://gamercred.onrender.com"
            )
            for position, (user_id, credits, games, most_played, most_played_hours) in enumerate(leaderboard[:10], 1):
                member = ctx.guild.get_member(user_id)
                username = member.display_name if member else f"User{user_id}"
                embed.add_field(
                    name=f"{position}. {username}",
                    value=f"💎 {credits:,.1f} cred\n🎮 {games} games\n🏆 Most played: {most_played} ({most_played_hours:,.1f}h)",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='monthly')
    async def monthly_leaderboard(self, ctx):
        """Show the monthly gamer cred leaderboard"""
        try:
            # Get current period and leaderboard
            period = await self.storage.get_or_create_current_period(LeaderboardType.MONTHLY)
            leaderboard = await self.storage.get_leaderboard_by_timeframe(LeaderboardType.MONTHLY, self.bot, period=period)

            if not leaderboard:
                await ctx.send("No gaming activity in the current month!")
                return

            # Record the placements in history
            await self.storage.record_leaderboard_placements(LeaderboardType.MONTHLY, leaderboard, period)

            embed = Embed(
                title="📅 Monthly Gamer Cred Leaderboard",
                description=f"Period: {self.format_cst_time(period.start_time)} to {self.format_cst_time(period.end_time)}\nResets on the 1st of each month at 00:00 CST",
                color=0x00ff00,
                url="https://gamercred.onrender.com"
            )
            for position, (user_id, credits, games, most_played, most_played_hours) in enumerate(leaderboard[:10], 1):
                member = ctx.guild.get_member(user_id)
                username = member.display_name if member else f"User{user_id}"
                embed.add_field(
                    name=f"{position}. {username}",
                    value=f"💎 {credits:,.1f} cred\n🎮 {games} games\n🏆 Most played: {most_played} ({most_played_hours:,.1f}h)",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='placement_history')
    async def show_placement_history(self, ctx, member: Optional[discord.Member] = None):
        """Show a user's leaderboard placement history"""
        try:
            target_user = member or ctx.author
            history = self.storage.get_user_placement_history(target_user.id)

            if not history:
                await ctx.send(f"{target_user.display_name} hasn't placed in any leaderboards yet!")
                return

            embed = Embed(
                title=f"🏆 Leaderboard History for {target_user.display_name}",
                color=0x00ff00
            )
            embed.set_footer(text="🌐 View on Gamer Cred", icon_url="https://gamercred.onrender.com/favicon.ico")

            # Group history by type
            weekly_history = [h for h in history if h['type'] == 'weekly'][:5]  # Last 5 weekly placements
            monthly_history = [h for h in history if h['type'] == 'monthly'][:5]  # Last 5 monthly placements

            if weekly_history:
                weekly_value = ""
                for h in weekly_history:
                    weekly_value += (
                        f"**{self.get_ordinal_suffix(h['placement'])} Place** ({self.format_cst_time(h['period_start'])} to {self.format_cst_time(h['period_end'])})\n"
                        f"💎 {h['credits']:,.1f} cred • 🎮 {h['games_played']} games\n"
                        f"🏆 Most played: {h['most_played_game']} ({h['most_played_hours']:,.1f}h)\n"
                        f"──────────────\n"
                    )
                embed.add_field(
                    name="📅 Recent Weekly Placements",
                    value=weekly_value.strip(),
                    inline=False
                )

            if monthly_history:
                monthly_value = ""
                for h in monthly_history:
                    monthly_value += (
                        f"**{self.get_ordinal_suffix(h['placement'])} Place** ({self.format_cst_time(h['period_start'])} to {self.format_cst_time(h['period_end'])})\n"
                        f"💎 {h['credits']:,.1f} cred • 🎮 {h['games_played']} games\n"
                        f"🏆 Most played: {h['most_played_game']} ({h['most_played_hours']:,.1f}h)\n"
                        f"──────────────\n"
                    )
                embed.add_field(
                    name="📅 Recent Monthly Placements",
                    value=monthly_value.strip(),
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='history')
    async def show_history(self, ctx):
        """Show your gaming history and totals per game"""
        try:
            history = self.storage.get_user_gaming_history(str(ctx.author.id))
            summaries = self.storage.get_user_game_summaries(str(ctx.author.id))

            if not history:
                await ctx.send("You haven't logged any gaming sessions yet!")
                return

            # Create embed for recent sessions (limit to 10)
            sessions_embed = Embed(
                title=f"🎮 Recent Gaming Sessions for {ctx.author.display_name}",
                color=0x0088ff
            )
            sessions_embed.set_footer(text="🌐 View on Gamer Cred", icon_url="https://gamercred.onrender.com/favicon.ico")

            for session in history[:10]:  # Limit to 10 sessions
                sessions_embed.add_field(
                    name=f"{session['game']} ({session['timestamp'].strftime('%Y-%m-%d')})",
                    value=f"Hours: {session['hours']:,.1f}\nCredits: {session['credits_earned']:,.1f}\nRate: {session['rate']:,.1f} cred/hour",
                    inline=False
                )

            await ctx.send(embed=sessions_embed)

            # Create embed for game summaries (limit to 20 games)
            if summaries:
                summary_embed = Embed(
                    title=f"📊 Game Totals for {ctx.author.display_name}",
                    color=0x00ff00
                )
                summary_embed.set_footer(text="🌐 View on Gamer Cred", icon_url="https://gamercred.onrender.com/favicon.ico")

                for summary in summaries[:20]:  # Limit to 20 games
                    summary_embed.add_field(
                        name=summary['game'],
                        value=f"⏱️ {summary['total_hours']:,.1f} hours in {summary['sessions']} sessions\n💎 {summary['total_credits']:,.1f} cred earned",
                        inline=True
                    )

                await ctx.send(embed=summary_embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='achievements')
    async def show_achievements(self, ctx):
        """Show your gaming achievements"""
        try:
            achievements = self.storage.get_user_achievements(ctx.author.id)

            # Achievement categories and their descriptions
            achievement_categories = {
                "⏱️ Time": {
                    'novice_gamer': ('Novice', '10h+'),
                    'veteran_gamer': ('Veteran', '100h+'),
                    'gaming_legend': ('Legend', '1000h+'),
                    'gaming_god': ('God', '5000h+')
                },
                "💎 Credits": {
                    'credit_starter': ('Starter', '10+'),
                    'credit_collector': ('Collector', '100+'),
                    'credit_hoarder': ('Hoarder', '1000+'),
                    'credit_baron': ('Baron', '10k+'),
                    'credit_millionaire': ('Millionaire', '1M+')
                },
                "🎮 Games": {
                    'game_curious': ('Curious', '3+'),
                    'game_explorer': ('Explorer', '5+'),
                    'game_adventurer': ('Adventurer', '10+'),
                    'game_connoisseur': ('Connoisseur', '20+'),
                    'game_master': ('Master', '50+')
                },
                "⚡ Sessions": {
                    'gaming_sprint': ('Sprint', '1h+'),
                    'gaming_marathon': ('Marathon', '5h+'),
                    'gaming_ultramarathon': ('Ultra', '12h+'),
                    'gaming_immortal': ('Immortal', '24h+')
                },
                "📈 Skills": {
                    'efficient_gamer': ('Efficient', '2+/h'),
                    'pro_gamer': ('Pro', '5+/h'),
                    'elite_gamer': ('Elite', '10+/h'),
                    'legendary_gamer': ('Legend', '100+/h')
                },
                "💪 Dedication": {
                    'game_enthusiast': ('Enthusiast', '1×10h'),
                    'game_devotee': ('Devotee', '3×10h'),
                    'game_zealot': ('Zealot', '5×10h'),
                    'game_fanatic': ('Fanatic', '10×10h')
                }
            }

            # Create embed
            embed = Embed(
                title=f"🌟 Achievements for {ctx.author.display_name}",
                color=0x00ff00
            )
            embed.set_footer(text="🌐 View on Gamer Cred", icon_url="https://gamercred.onrender.com/favicon.ico")

            # Add each category
            for category, achievements_dict in achievement_categories.items():
                category_value = ""
                for achievement_id, (name, requirement) in achievements_dict.items():
                    status = "✅" if achievements.get(achievement_id, False) else "❌"
                    category_value += f"{status} **{name}** ({requirement})\n"
                embed.add_field(
                    name=category,
                    value=category_value.strip(),
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='gamestats')
    async def show_game_stats(self, ctx, *, game: Optional[str] = None):
        """Show detailed statistics for a specific game"""
        try:
            if not game:
                await ctx.send("❌ Please provide a game name (!gamestats <game>)")
                return

            stats = self.storage.get_game_stats(game)
            if not stats:
                await ctx.send(f"❓ Game '{game}' not found in database\n🌐 View on [Gamer Cred](https://gamercred.onrender.com)")
                return

            embed = Embed(title=f"📊 Stats for {stats['name']}", color=0x00ff00)
            embed.set_footer(text="🌐 View on Gamer Cred", icon_url="https://gamercred.onrender.com/favicon.ico")
            embed.add_field(
                name="Total Hours Played",
                value=f"⏱️ {stats['total_hours']:,.1f} hours",
                inline=True
            )
            embed.add_field(
                name="Total Credits Earned",
                value=f"💎 {stats['total_credits']:,.1f} cred",
                inline=True
            )
            embed.add_field(
                name="Credit Rate",
                value=f"📈 {stats['credits_per_hour']:,.1f} cred/hour",
                inline=True
            )
            embed.add_field(
                name="Gaming Sessions",
                value=f"🎮 {stats['total_sessions']} sessions",
                inline=True
            )
            embed.add_field(
                name="Unique Players",
                value=f"👥 {stats['unique_players']} players",
                inline=True
            )
            embed.add_field(
                name="Added By",
                value=f"👤 <@{stats['added_by']}>",
                inline=True
            )

            # Add Backloggd link if available
            if 'backloggd_url' in stats:
                embed.add_field(
                    name="View on Backloggd",
                    value=f"🔗 [Game Page]({stats['backloggd_url']})",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    async def show_my_game_stats(self, ctx, game: str):
        """Helper function to show game-specific stats"""
        try:
            stats = self.storage.get_user_game_stats(ctx.author.id, game)
            if not stats:
                await ctx.send(f"❓ You haven't played '{game}' yet!")
                return

            embed = Embed(title=f"📊 Your Stats for {stats['name']}", color=0x00ff00)
            embed.set_footer(text="🌐 View on Gamer Cred", icon_url="https://gamercred.onrender.com/favicon.ico")
            embed.add_field(
                name="Your Total Hours",
                value=f"⏱️ {stats['total_hours']:,.1f} hours",
                inline=True
            )
            embed.add_field(
                name="Your Total Credits",
                value=f"💎 {stats['total_credits']:,.1f} cred",
                inline=True
            )
            embed.add_field(
                name="Credit Rate",
                value=f"📈 {stats['credits_per_hour']:,.1f} cred/hour",
                inline=True
            )
            embed.add_field(
                name="Your Gaming Sessions",
                value=f"🎮 {stats['total_sessions']} sessions",
                inline=True
            )
            embed.add_field(
                name="First Played",
                value=f"📅 {stats['first_played'].strftime('%Y-%m-%d')}",
                inline=True
            )
            embed.add_field(
                name="Last Played",
                value=f"🕒 {stats['last_played'].strftime('%Y-%m-%d')}",
                inline=True
            )

            # Add Backloggd link if available
            if 'backloggd_url' in stats:
                embed.add_field(
                    name="View on Backloggd",
                    value=f"🔗 [Game Page]({stats['backloggd_url']})",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='mystats')
    async def show_my_stats(self, ctx, *, game: Optional[str] = None):
        """Show your gaming statistics (overall or per game)"""
        try:
            if game:
                # Show game-specific stats
                await self.show_my_game_stats(ctx, game)
                return

            # Get overall stats
            stats = self.storage.get_user_overall_stats(str(ctx.author.id))
            if not stats:
                await ctx.send("You haven't logged any gaming sessions yet!")
                return

            # Create embed
            embed = Embed(
                title=f"📊 Gaming Stats for {ctx.author.display_name}",
                color=0x00ff00
            )
            embed.set_footer(text="🌐 View on Gamer Cred", icon_url="https://gamercred.onrender.com/favicon.ico")

            # Add overall stats
            embed.add_field(
                name="Overall Stats",
                value=(
                    f"⏱️ Total Hours: {stats['total_hours']:,.1f}\n"
                    f"💎 Total Credits: {stats['total_credits']:,.1f}\n"
                    f"🎮 Games Played: {stats['games_played']}\n"
                    f"📅 Sessions: {stats['total_sessions']}"
                ),
                inline=False
            )

            # Add time range
            if stats['first_played'] and stats['last_played']:
                embed.add_field(
                    name="Time Range",
                    value=(
                        f"📅 First Played: {self.format_cst_time(stats['first_played'])}\n"
                        f"🕒 Last Played: {self.format_cst_time(stats['last_played'])}"
                    ),
                    inline=False
                )

            # Add most played game
            if stats['most_played_game']:
                embed.add_field(
                    name="Most Played Game",
                    value=f"🎮 {stats['most_played_game']} ({stats['most_played_hours']:,.1f}h)",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='help')
    async def show_help(self, ctx):
        """Show help message with available commands"""
        embed = Embed(
            title="📖 Gamer Cred Bot Commands",
            description="Track your gaming progress and earn achievements!",
            color=0x0088ff
        )
        embed.set_footer(text="🌐 View on Gamer Cred", icon_url="https://gamercred.onrender.com/favicon.ico")

        # Core Commands
        embed.add_field(
            name="📱 CORE COMMANDS",
            value="━━━━━━━━━━━━━━━",
            inline=False
        )
        embed.add_field(
            name="!log <hours> <game>",
            value="Log your gaming hours",
            inline=False
        )
        embed.add_field(
            name="!balance",
            value="Check your gamer cred balance",
            inline=False
        )
        embed.add_field(
            name="!history",
            value="View your gaming history",
            inline=False
        )
        embed.add_field(
            name="!mystats [game]",
            value="Show your gaming statistics (overall or per game)",
            inline=False
        )
        embed.add_field(
            name="!achievements",
            value="View your gaming achievements",
            inline=False
        )

        # Competition Commands
        embed.add_field(
            name="🏆 LEADERBOARDS",
            value="━━━━━━━━━━━━━━━",
            inline=False
        )
        embed.add_field(
            name="!leaderboard",
            value="View the all-time gamer cred leaderboard",
            inline=False
        )
        embed.add_field(
            name="!weekly",
            value="View the weekly gamer cred leaderboard",
            inline=False
        )
        embed.add_field(
            name="!monthly",
            value="View the monthly gamer cred leaderboard",
            inline=False
        )

        # Game Management
        embed.add_field(
            name="🎮 GAME MANAGEMENT",
            value="━━━━━━━━━━━━━━━",
            inline=False
        )
        embed.add_field(
            name="!rate <game>",
            value="Check credits per hour for a game",
            inline=False
        )
        embed.add_field(
            name="!setrate <credits> <game>",
            value="Set credits per hour for a game",
            inline=False
        )
        embed.add_field(
            name="!gamestats <game>",
            value="View detailed statistics for a specific game",
            inline=False
        )
        embed.add_field(
            name="!userstats @user [game]",
            value="View another user's gaming statistics",
            inline=False
        )

        # Admin Commands
        embed.add_field(
            name="⚙️ ADMIN COMMANDS",
            value="━━━━━━━━━━━━━━━",
            inline=False
        )
        embed.add_field(
            name="!addbonus @user <amount> <reason>",
            value="Add or remove bonus cred (Mod only)",
            inline=False
        )
        embed.add_field(
            name="!renamegame \"Old Name\" \"New Name\"",
            value="Rename a game (Mod only)",
            inline=False
        )
        embed.add_field(
            name="!deletegame <game>",
            value="Delete a game from the database (Mod only)",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command(name='addbonus')
    @commands.has_permissions(manage_messages=True)  # Require moderator permissions
    async def add_bonus_credits(self, ctx, user: discord.Member, credits: str, *, reason: Optional[str] = None):
        """Add bonus gamer cred to a user (Moderator only)"""
        try:
            # Validate inputs
            try:
                credits_float = float(credits)
            except ValueError:
                await ctx.send("❌ Please provide a valid number for credits")
                return

            if not reason:
                await ctx.send("❌ Please provide a reason for the credit adjustment")
                return

            # Add the bonus credits
            new_total = self.storage.add_bonus_credits(user.id, credits_float, reason, ctx.author.id)

            # Determine if this is an addition or reduction
            action_word = "added to" if credits_float > 0 else "removed from"
            credits_display = abs(credits_float)  # Use absolute value for display

            # Send confirmation messages
            await ctx.send(
                f"✨ {credits_display:,.1f} cred {action_word} {user.display_name}!\n"
                f"📝 Reason: {reason}\n"
                f"💎 New total: {new_total:,.1f} cred"
            )

            # DM the user about their bonus/reduction
            try:
                message = (
                    f"🎉 You received {credits_display:,.1f} cred from {ctx.author.display_name}!"
                    if credits_float > 0
                    else f"📉 {credits_display:,.1f} cred was removed by {ctx.author.display_name}"
                )
                await user.send(
                    f"{message}\n"
                    f"📝 Reason: {reason}\n"
                    f"💎 Your new total: {new_total:,.1f} cred"
                )
            except discord.Forbidden:
                pass  # User has DMs disabled

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @add_bonus_credits.error
    async def add_bonus_credits_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need moderator permissions to use this command")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Please provide a user and amount (!addbonus @user <amount> <reason>)")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")

    @commands.command(name='renamegame')
    @commands.has_permissions(manage_messages=True)  # Require moderator permissions
    async def rename_game(self, ctx, old_name: str, *, new_name: str):
        """Rename a game in the system (Moderator only)"""
        try:
            # Get original game info first
            old_game_info = self.storage.get_game_info(old_name)
            if not old_game_info:
                await ctx.send(f"❌ Game '{old_name}' not found in database")
                return

            # Try to rename the game
            result = self.storage.rename_game(old_name, new_name, ctx.author.id)
            if not result:
                await ctx.send(f"❌ Failed to rename game. '{new_name}' might already exist.")
                return

            # Send confirmation with details
            await ctx.send(
                f"✅ Successfully renamed game!\n"
                f"📝 Old name: {result['old_name']}\n"
                f"📝 New name: {result['new_name']}\n"
                f"📊 Rate: {result['credits_per_hour']:,.1f} cred/hour\n"
                f"👤 Originally added by: <@{result['added_by']}>"
            )

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @rename_game.error
    async def rename_game_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need moderator permissions to use this command")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Please provide both names (!renamegame \"Old Name\" \"New Name\")")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")

    @commands.command(name='deletegame')
    @commands.has_permissions(manage_messages=True)  # Require moderator permissions
    async def delete_game(self, ctx, *, game: Optional[str] = None):
        """Delete a game from the database (Moderator only)"""
        try:
            if not game:
                await ctx.send("❌ Please provide a game name (!deletegame <game>)")
                return

            # Try to delete the game
            result = self.storage.delete_game(game)
            if not result:
                await ctx.send(f"❌ Game '{game}' not found in database")
                return

            # Create confirmation embed with game stats
            embed = Embed(title=f"🗑️ Game Deleted: {result['name']}", color=0xff0000)
            embed.add_field(
                name="Game Stats",
                value=(
                    f"⏱️ Total Hours: {result['total_hours']:,.1f}\n"
                    f"💎 Total Credits: {result['total_credits']:,.1f}\n"
                    f"📊 Rate: {result['credits_per_hour']:,.1f} cred/hour\n"
                    f"🎮 Sessions: {result['total_sessions']:,}\n"
                    f"👥 Players: {result['unique_players']:,}\n"
                    f"👤 Added by: <@{result['added_by']}>"
                ),
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @delete_game.error
    async def delete_game_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need moderator permissions to use this command")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Please provide a game name (!deletegame <game>)")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")

    @commands.command(name='userstats')
    async def show_user_stats(self, ctx, *, args: Optional[str] = None):
        """Show gaming statistics for another user, optionally for a specific game"""
        try:
            if not args:
                await ctx.send("❌ Please provide a user to view their stats (!userstats @user or !userstats username [game])")
                return

            # Split args into words
            args_parts = args.split()
            if not args_parts:
                await ctx.send("❌ Please provide a user to view their stats (!userstats @user or !userstats username [game])")
                return

            # Try to find the user - first check if it's a mention
            member = None
            game = None
            
            # Check if the first part is a mention
            if args_parts[0].startswith('<@') and args_parts[0].endswith('>'):
                try:
                    user_id = ''.join(filter(str.isdigit, args_parts[0]))
                    member = ctx.guild.get_member(int(user_id))
                    # If there are more parts, they form the game name
                    if len(args_parts) > 1:
                        game = ' '.join(args_parts[1:])
                except (ValueError, TypeError):
                    pass
            
            # If not a mention, try to find by display name
            if not member:
                # Try to find the user by their exact display name
                member = discord.utils.find(
                    lambda m: m.display_name.lower() == args.lower(),
                    ctx.guild.members
                )
                
                # If member is found and there's a game part, extract it
                if member:
                    game = None  # No game part since we used the full string as username
                else:
                    # Try to find the last possible game name by checking each possible split
                    for i in range(len(args_parts) - 1, -1, -1):
                        potential_username = ' '.join(args_parts[:i])
                        potential_game = ' '.join(args_parts[i:])
                        
                        member = discord.utils.find(
                            lambda m: m.display_name.lower() == potential_username.lower(),
                            ctx.guild.members
                        )
                        
                        if member:
                            game = potential_game
                            break

            if not member:
                await ctx.send("❌ Could not find that user. Please use their exact display name or mention them with @")
                return

            if game:
                # If game is specified, show game-specific stats
                await self.show_other_user_game_stats(ctx, member, game)
                return

            # Get user's overall stats
            summaries = self.storage.get_user_game_summaries(member.id)
            if not summaries:
                await ctx.send(f"{member.display_name} hasn't logged any gaming sessions yet!")
                return

            # Calculate overall stats
            total_hours = sum(s['total_hours'] for s in summaries)
            total_credits = sum(s['total_credits'] for s in summaries)
            unique_games = len(summaries)
            avg_credits_per_hour = total_credits / total_hours if total_hours > 0 else 0

            # Sort games by hours played to find most played
            sorted_games = sorted(summaries, key=lambda x: x['total_hours'], reverse=True)
            top_games = sorted_games[:5]  # Get top 5 most played games

            # Get placement history
            history = self.storage.get_user_placement_history(member.id)
            weekly_history = [h for h in history if h['type'] == 'weekly'][:3]  # Last 3 weekly placements
            monthly_history = [h for h in history if h['type'] == 'monthly'][:3]  # Last 3 monthly placements

            # Create embed for stats
            embed = Embed(
                title=f"📊 Gaming Stats for {member.display_name}",
                color=0x00ff00
            )

            # Overall stats section
            stats_section = (
                f"⏱️ **Total Time:** {total_hours:,.1f} hours\n"
                f"💎 **Total Credits:** {total_credits:,.1f} cred\n"
                f"🎮 **Games Played:** {unique_games:,} different games\n"
                f"📈 **Average Rate:** {avg_credits_per_hour:,.1f} cred/hour\n"
            )
            embed.add_field(name="Overall Statistics", value=stats_section, inline=False)

            # Recent placements section
            if weekly_history or monthly_history:
                placements_section = ""
                
                if weekly_history:
                    placements_section += "**Weekly Rankings:**\n"
                    for h in weekly_history:
                        placements_section += (
                            f"• {self.get_ordinal_suffix(h['placement'])} Place ({self.format_cst_time(h['period_start'])})\n"
                            f"  💎 {h['credits']:,.1f} cred • 🎮 {h['games_played']} games\n"
                        )
                
                if monthly_history:
                    if weekly_history:
                        placements_section += "\n"  # Add spacing between weekly and monthly
                    placements_section += "**Monthly Rankings:**\n"
                    for h in monthly_history:
                        placements_section += (
                            f"• {self.get_ordinal_suffix(h['placement'])} Place ({self.format_cst_time(h['period_start'])})\n"
                            f"  💎 {h['credits']:,.1f} cred • 🎮 {h['games_played']} games\n"
                        )
                
                embed.add_field(
                    name="🏆 Recent Rankings",
                    value=placements_section,
                    inline=False
                )

            # Most played games section
            if top_games:
                most_played = ""
                for i, game in enumerate(top_games, 1):
                    most_played += (
                        f"{'═' * 40}\n"  # Top border
                        f"**#{i} │ {game['game']}**\n"
                        f"──────────────────\n"  # Separator under title
                        f"⏱️ **Time:** {game['total_hours']:,.1f} hours\n"
                        f"💎 **Credits:** {game['total_credits']:,.1f} cred\n"
                        f"📊 **Rate:** {game['rate']:,.1f} cred/hour\n"
                        f"🎲 **Sessions:** {game['sessions']}\n"
                    )
                # Add final border
                most_played += f"{'═' * 40}"
                
                embed.add_field(
                    name="🏆 Most Played Games",
                    value=most_played,
                    inline=False
                )

            # Get achievements
            achievements = self.storage.get_user_achievements(member.id)
            achieved = sum(1 for v in achievements.values() if v)
            total = len(achievements)
            embed.add_field(
                name="🌟 Achievements Progress",
                value=f"{achieved} out of {total} achievements unlocked",
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    async def show_other_user_game_stats(self, ctx, member: discord.Member, game: str):
        """Helper function to show game-specific stats for another user"""
        try:
            stats = self.storage.get_user_game_stats(member.id, game)
            if not stats:
                await ctx.send(f"❓ {member.display_name} hasn't played '{game}' yet!")
                return

            embed = Embed(title=f"📊 {member.display_name}'s Stats for {stats['name']}", color=0x00ff00)
            embed.add_field(
                name="Total Hours",
                value=f"⏱️ {stats['total_hours']:,.1f} hours",
                inline=True
            )
            embed.add_field(
                name="Total Credits",
                value=f"💎 {stats['total_credits']:,.1f} cred",
                inline=True
            )
            embed.add_field(
                name="Credit Rate",
                value=f"📈 {stats['credits_per_hour']:,.1f} cred/hour",
                inline=True
            )
            embed.add_field(
                name="Gaming Sessions",
                value=f"🎮 {stats['total_sessions']} sessions",
                inline=True
            )
            embed.add_field(
                name="First Played",
                value=f"`📅 {stats['first_played'].strftime('%Y-%m-%d')}",
                inline=True
            )
            embed.add_field(
                name="Last Played",
                value=f"🕒 {stats['last_played'].strftime('%Y-%m-%d')}",
                inline=True
            )

            # Add Backloggd link if available
            if 'backloggd_url' in stats:
                embed.add_field(
                    name="View on Backloggd",
                    value=f"🔗 [Game Page]({stats['backloggd_url']})",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @tasks.loop(minutes=1)  # Check every minute instead of every 5 minutes
    async def check_periods(self):
        """Background task to check if periods have ended"""
        try:
            print("\nChecking leaderboard periods...")
            
            # Get current time in UTC first
            utc_now = datetime.now(pytz.UTC)
            # Convert to CST
            now = utc_now.astimezone(self.storage.cst)
            print(f"Current time - UTC: {utc_now}, CST: {now}")
            
            # Check weekly period
            weekly_period = await self.storage.get_or_create_current_period(LeaderboardType.WEEKLY)
            print(f"Weekly period: {weekly_period.start_time} to {weekly_period.end_time} CST")
            
            # Check monthly period
            monthly_period = await self.storage.get_or_create_current_period(LeaderboardType.MONTHLY)
            print(f"Monthly period: {monthly_period.start_time} to {monthly_period.end_time} CST")
            
            # Check if either period has ended
            if now >= weekly_period.end_time:
                print("Weekly period has ended - forcing transition")
                session = self.storage.Session()
                try:
                    # Get current placements before ending period
                    placements = await self.storage.get_leaderboard_by_timeframe(LeaderboardType.WEEKLY, self.bot)
                    await self.storage.record_leaderboard_placements(LeaderboardType.WEEKLY, placements)
                    
                    # End current period
                    weekly_period.is_active = False
                    session.commit()
                    
                    # Make announcement
                    await self.storage.announce_period_end(self.bot, LeaderboardType.WEEKLY, weekly_period)
                    
                    # Create new period in the same session
                    new_period = LeaderboardPeriod(
                        leaderboard_type=LeaderboardType.WEEKLY,
                        start_time=weekly_period.end_time,
                        end_time=weekly_period.end_time + timedelta(days=7),
                        is_active=True
                    )
                    session.add(new_period)
                    session.commit()
                    print("Created new weekly period")
                finally:
                    session.close()
            
            if now >= monthly_period.end_time:
                print("Monthly period has ended - forcing transition")
                session = self.storage.Session()
                try:
                    # Get current placements before ending period
                    placements = await self.storage.get_leaderboard_by_timeframe(LeaderboardType.MONTHLY, self.bot)
                    await self.storage.record_leaderboard_placements(LeaderboardType.MONTHLY, placements)
                    
                    # End current period
                    monthly_period.is_active = False
                    session.commit()
                    
                    # Make announcement
                    await self.storage.announce_period_end(self.bot, LeaderboardType.MONTHLY, monthly_period)
                    
                    # Create new period in the same session
                    new_period = LeaderboardPeriod(
                        leaderboard_type=LeaderboardType.MONTHLY,
                        start_time=monthly_period.end_time,
                        end_time=monthly_period.end_time.replace(day=1) + timedelta(days=32),
                        is_active=True
                    )
                    session.add(new_period)
                    session.commit()
                    print("Created new monthly period")
                finally:
                    session.close()
            
        except Exception as e:
            print(f"Error checking periods: {str(e)}")
            import traceback
            print(traceback.format_exc())