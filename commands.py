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
            except ValueError:
                await ctx.send(MESSAGES['invalid_hours'])
                return

            # Get game info before logging
            game_info = self.storage.get_game_info(game)

            # Log hours and get earned credits
            credits = self.storage.add_gaming_hours(ctx.author.id, hours_float, game)

            # Generate Backloggd URL
            backloggd_url = self.get_backloggd_url(game)

            # Determine if this is an addition or reduction
            action_word = "logged" if hours_float > 0 else "removed"
            hours_display = abs(hours_float)  # Use absolute value for display
            credits_display = abs(credits)  # Use absolute value for display

            # Create detailed response
            if game_info:
                await ctx.send(
                    f"✅ Successfully {action_word} {hours_display:,.1f} hours for {game}!\n"
                    f"📊 Rate: {game_info['credits_per_hour']:,.1f} cred/hour\n"
                    f"💎 {'Earned' if credits > 0 else 'Removed'} {credits_display:,.1f} cred!\n"
                    f"🎮 View on Backloggd: {backloggd_url}"
                )
            else:
                await ctx.send(MESSAGES['success_log'].format(
                    action=action_word,
                    hours=f"{hours_display:,.1f}",
                    game=game,
                    credits=f"{credits_display:,.1f}",
                    earned="Earned" if credits > 0 else "Removed"
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
                if credits_float < 0.1:
                    await ctx.send("❌ Credits per hour must be at least 0.1")
                    return
            except ValueError:
                await ctx.send("❌ Please provide a valid number for credits per hour")
                return

            if self.storage.set_game_credits_per_hour(game, credits_float, ctx.author.id):
                await ctx.send(f"✅ Set rate for {game} to {credits_float:,.1f} cred/hour!")
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
                    f"📊 Rate for {game}: {game_info['credits_per_hour']:,.1f} cred/hour\n"
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
                await ctx.send(MESSAGES['balance'].format(credits=f"{credits:,.1f}"))
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
            leaderboard = self.storage.get_leaderboard_by_timeframe(days=7)

            if not leaderboard:
                await ctx.send(MESSAGES['no_data'])
                return

            embed = Embed(title="📅 Weekly Gamer Cred Leaderboard", color=0x00ff00)

            for position, (user_id, credits, games) in enumerate(leaderboard[:10], 1):
                member = ctx.guild.get_member(user_id)
                username = member.display_name if member else f"User{user_id}"
                embed.add_field(
                    name=f"{position}. {username}",
                    value=f"{credits:,.1f} cred (🎮 {games} games)",
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
                member = ctx.guild.get_member(user_id)
                username = member.display_name if member else f"User{user_id}"
                embed.add_field(
                    name=f"{position}. {username}",
                    value=f"{credits:,.1f} cred (🎮 {games} games)",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='history')
    async def show_history(self, ctx):
        """Show your gaming history and totals per game"""
        try:
            history = self.storage.get_user_gaming_history(ctx.author.id)
            summaries = self.storage.get_user_game_summaries(ctx.author.id)

            if not history:
                await ctx.send("You haven't logged any gaming sessions yet!")
                return

            # Create embed for recent sessions
            sessions_embed = Embed(
                title=f"🎮 Recent Gaming Sessions for {ctx.author.display_name}",
                color=0x0088ff
            )

            for session in history:
                sessions_embed.add_field(
                    name=f"{session['game']} ({session['timestamp'].strftime('%Y-%m-%d')})",
                    value=f"Hours: {session['hours']:,.1f}\nCredits: {session['credits_earned']:,.1f}\nRate: {session['rate']:,.1f} cred/hour",
                    inline=False
                )

            await ctx.send(embed=sessions_embed)

            # Create embed for game summaries
            if summaries:
                summary_embed = Embed(
                    title=f"📊 Game Totals for {ctx.author.display_name}",
                    color=0x00ff00
                )

                for summary in summaries:
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

            embed = Embed(title=f"🏆 Achievements for {ctx.author.display_name}", color=0xffd700)

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

    @commands.command(name='gamestats')
    async def show_game_stats(self, ctx, *, game: Optional[str] = None):
        """Show detailed statistics for a specific game"""
        try:
            if not game:
                await ctx.send("❌ Please provide a game name (!gamestats <game>)")
                return

            stats = self.storage.get_game_stats(game)
            if not stats:
                await ctx.send(f"❓ Game '{game}' not found in database")
                return

            embed = Embed(title=f"📊 Stats for {stats['name']}", color=0x00ff00)
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

            # Add Backloggd link
            backloggd_url = self.get_backloggd_url(game)
            embed.add_field(
                name="View on Backloggd",
                value=f"🔗 [Game Page]({backloggd_url})",
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

            # Add Backloggd link
            backloggd_url = self.get_backloggd_url(game)
            embed.add_field(
                name="View on Backloggd",
                value=f"🔗 [Game Page]({backloggd_url})",
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(MESSAGES['error'].format(error=str(e)))

    @commands.command(name='mystats')
    async def show_my_stats(self, ctx, *, game: Optional[str] = None):
        """Show your personal gaming statistics, optionally for a specific game"""
        try:
            if game:
                # If game is specified, show game-specific stats
                await self.show_my_game_stats(ctx, game)
                return

            # Get user's overall stats
            summaries = self.storage.get_user_game_summaries(ctx.author.id)
            if not summaries:
                await ctx.send("You haven't logged any gaming sessions yet!")
                return

            # Calculate overall stats
            total_hours = sum(s['total_hours'] for s in summaries)
            total_credits = sum(s['total_credits'] for s in summaries)
            unique_games = len(summaries)
            avg_credits_per_hour = total_credits / total_hours if total_hours > 0 else 0

            # Sort games by hours played to find most played
            sorted_games = sorted(summaries, key=lambda x: x['total_hours'], reverse=True)
            top_games = sorted_games[:3]  # Get top 3 most played games

            # Create embed for overall stats
            embed = Embed(title=f"📊 Gaming Stats for {ctx.author.display_name}", color=0x00ff00)

            # Main stats
            embed.add_field(
                name="⏱️ Total Gaming Time",
                value=f"{total_hours:,.1f} hours",
                inline=True
            )
            embed.add_field(
                name="💎 Total Credits Earned",
                value=f"{total_credits:,.1f} cred",
                inline=True
            )
            embed.add_field(
                name="🎮 Games Played",
                value=f"{unique_games:,} different games",
                inline=True
            )
            embed.add_field(
                name="📈 Average Credits/Hour",
                value=f"{avg_credits_per_hour:,.1f} cred/hour",
                inline=True
            )

            # Most played games section
            most_played = "\n".join([
                f"**{i+1}. {game['game']}**\n"
                f"⏱️ {game['total_hours']:,.1f} hours • 💎 {game['total_credits']:,.1f} cred"
                for i, game in enumerate(top_games)
            ])
            embed.add_field(
                name="🏆 Most Played Games",
                value=most_played or "No games logged yet",
                inline=False
            )

            # Get achievements
            achievements = self.storage.get_user_achievements(ctx.author.id)
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
            'history': '!history - View your gaming history and totals per game',
            'achievements': '!achievements - View your achievements',
            'help': '!help - Show this help message',
            'gamestats': '!gamestats <game> - Show detailed game statistics',
            'mystats': '!mystats - Show your overall gaming statistics or use !mystats <game> for game-specific stats',
            'addbonus': '!addbonus @user <amount> <reason> - Add bonus credits (Moderator only)',
            'renamegame': '!renamegame "Old Name" "New Name" - Rename a game (Moderator only)'
        }

        for command, description in commands_with_descriptions.items():
            embed.add_field(name=command, value=description, inline=False)

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