import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy import create_engine, func, DateTime as sqlalchemy_DateTime, and_, Integer, String, BigInteger, text, distinct
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from models import Base, Game, UserStats, GamingSession, LeaderboardHistory, LeaderboardType, LeaderboardPeriod, Bonus
import pytz
import discord
from dotenv import load_dotenv
import aiohttp
import asyncio
from collections import defaultdict
from sqlalchemy.sql import select
import traceback
import time
import sys
import logging

# Load environment variables
load_dotenv()

# Get database URL from environment variables
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

logger = logging.getLogger(__name__)

class GameStorage:
    def __init__(self):
        """Initialize the storage with database connection"""
        self.database_url = os.getenv('DATABASE_URL') or os.getenv('LOCAL_DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL or LOCAL_DATABASE_URL environment variable is not set")
        
        self._initialize_db()
        self.cst = pytz.timezone('America/Chicago')

    def get_session(self):
        """Get a database session with retry logic"""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                return self.Session()
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    logger.error(f"Failed to get database session after {max_retries} attempts: {str(e)}")
                    raise
                logger.warning(f"Database connection attempt {attempt + 1} failed: {str(e)}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

    def _initialize_db(self):
        """Initialize the database connection"""
        try:
            logger.info("Initializing database connection")
            self.engine = create_engine(self.database_url)
            self.Session = scoped_session(
                sessionmaker(
                    bind=self.engine,
                    expire_on_commit=False
                )
            )
            logger.info("Database connection initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}", exc_info=True)
            raise

    async def get_or_create_game(self, game_name: str, user_id: int, credits_per_hour: float = 1.0) -> Tuple[Game, bool]:
        """Get or create a game in the database"""
        session = self.Session()
        try:
            # Format the game name
            formatted_name = ' '.join(word.capitalize() for word in game_name.split())
            
            # Check if game exists
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(formatted_name)).first()
            created = False

            if not game:
                # Create the Backloggd URL
                url_name = formatted_name.lower()
                url_name = url_name.replace("'", "").replace('"', "")
                url_name = ''.join(c if c.isalnum() else '-' for c in url_name)
                url_name = '-'.join(filter(None, url_name.split('-')))
                
                backloggd_url = f"https://www.backloggd.com/games/{url_name}/"
                
                game = Game(
                    name=formatted_name, 
                    credits_per_hour=credits_per_hour, 
                    added_by=user_id,
                    backloggd_url=backloggd_url
                )
                session.add(game)
                session.commit()  # Commit to get the game ID
                created = True

            # Fetch and update RAWG data if missing
            if game and (game.rawg_id is None or game.box_art_url is None):
                rawg_details = await self.fetch_game_details_from_rawg(game.name)
                if rawg_details:
                    logger.debug(f"Updating game with RAWG details: {rawg_details}")
                    game.rawg_id = rawg_details.get('rawg_id')
                    game.box_art_url = rawg_details.get('box_art_url')
                    game.release_date = rawg_details.get('release_date')
                    game.description = rawg_details.get('description')
                    session.add(game)
                    session.commit()  # Commit RAWG data updates

            return game, created
        except Exception as e:
            session.rollback()
            logger.error(f"Error in get_or_create_game: {str(e)}", exc_info=True)
            raise
        finally:
            session.close()

    async def fetch_game_details_from_rawg(self, game_name: str) -> Optional[Dict[str, Any]]:
        """Fetch game details from RAWG API"""
        rawg_api_key = os.getenv('RAWG_API_KEY')
        rawg_api_url = os.getenv('RAWG_API_URL', 'https://api.rawg.io/api')
        
        if not rawg_api_key:
            logger.warning("RAWG_API_KEY not set")
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{rawg_api_url}/games',
                    params={
                        'key': rawg_api_key,
                        'search': game_name,
                        'page_size': 1
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data.get('results'):
                            game = data['results'][0]
                            game_id = game.get('id')
                            if game_id:
                                async with session.get(
                                    f'{rawg_api_url}/games/{game_id}',
                                    params={'key': rawg_api_key}
                                ) as detail_response:
                                    if detail_response.status == 200:
                                        detail_data = await detail_response.json()
                                        return {
                                            'rawg_id': game.get('id'),
                                            'box_art_url': game.get('background_image'),
                                            'release_date': game.get('released'),
                                            'description': detail_data.get('description_raw', ''),
                                            'backloggd_url': f"https://www.backloggd.com/games/{game.get('slug')}/"
                                        }
                            return {
                                'rawg_id': game.get('id'),
                                'box_art_url': game.get('background_image'),
                                'release_date': game.get('released'),
                                'description': game.get('description_raw', ''),
                                'backloggd_url': f"https://www.backloggd.com/games/{game.get('slug')}/"
                            }
                    return None
        except Exception as e:
            logger.error(f"Error fetching RAWG data: {str(e)}", exc_info=True)
            return None

    async def announce_period_end(self, bot: discord.Client, leaderboard_type: LeaderboardType, old_period: LeaderboardPeriod) -> None:
        """Create an announcement for the end of a leaderboard period"""
        session = self.Session()
        try:
            # Get the final placements for the period
            placements = session.query(LeaderboardHistory)\
                .filter(
                    LeaderboardHistory.period_id == old_period.id,
                    LeaderboardHistory.leaderboard_type == leaderboard_type
                )\
                .order_by(LeaderboardHistory.placement)\
                .all()

            if not placements:
                return

            # Create the announcement embed
            period_type = "Weekly" if leaderboard_type == LeaderboardType.WEEKLY else "Monthly"
            # Times are already in CST, no conversion needed
            period_start = old_period.start_time
            period_end = old_period.end_time

            embed = discord.Embed(
                title=f"🏆 {period_type} Leaderboard Results",
                description=f"Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}",
                color=0xffd700  # Gold color
            )

            # Add placements to the embed
            for placement in placements:
                # Get member object
                for guild in bot.guilds:  # Search all guilds bot is in
                    member = guild.get_member(placement.user_id)
                    if member:
                        break

                username = member.display_name if member else f"User{placement.user_id}"

                # Get ordinal suffix for placement
                if placement.placement == 1:
                    medal = "🥇"
                elif placement.placement == 2:
                    medal = "🥈"
                elif placement.placement == 3:
                    medal = "🥉"
                else:
                    medal = "🎮"

                # Get ordinal suffix
                if 10 <= placement.placement % 100 <= 20:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(placement.placement % 10, 'th')

                embed.add_field(
                    name=f"{medal} {placement.placement}{suffix} Place: {username}",
                    value=(
                        f"💎 {placement.credits:,.1f} credits earned\n"
                        f"🎮 {placement.games_played} games played\n"
                        f"🏆 Most played: {placement.most_played_game} ({placement.most_played_hours:,.1f}h)"
                    ),
                    inline=False
                )

            # Send the announcement to all guilds
            for guild in bot.guilds:
                # Try to find a suitable channel to send the announcement
                # Priority: channel with 'leaderboard' in name, then 'gaming', then 'general', then first text channel
                announcement_channel = None
                for channel in guild.text_channels:
                    if 'leaderboard' in channel.name.lower():
                        announcement_channel = channel
                        break
                    elif 'gaming' in channel.name.lower() and not announcement_channel:
                        announcement_channel = channel
                    elif 'general' in channel.name.lower() and not announcement_channel:
                        announcement_channel = channel

                if not announcement_channel and guild.text_channels:
                    announcement_channel = guild.text_channels[0]

                if announcement_channel:
                    try:
                        await announcement_channel.send(embed=embed)
                    except discord.errors.Forbidden:
                        print(f"Cannot send messages in {announcement_channel.name} ({guild.name})")
                    except Exception as e:
                        print(f"Error sending announcement in {guild.name}: {str(e)}")

        except Exception as e:
            print(f"Error creating leaderboard announcement: {str(e)}")
        finally:
            session.close()

    async def get_or_create_current_period(self, timeframe: LeaderboardType) -> LeaderboardPeriod:
        """Get or create the current leaderboard period."""
        try:
            with self.Session() as session:
                # Use enum name (uppercase) for PostgreSQL enum
                timeframe_str = timeframe.name
                cst = pytz.timezone('America/Chicago')
                now = datetime.now(cst)
                if timeframe in [LeaderboardType.WEEKLY, LeaderboardType.MONTHLY]:
                    start, end = get_period_boundaries(now, timeframe.value.lower())
                else:  # ALLTIME
                    start = datetime(2020, 1, 1, tzinfo=cst)
                    end = datetime(2100, 1, 1, tzinfo=cst)
                period = session.query(LeaderboardPeriod).filter_by(
                    leaderboard_type=timeframe_str,
                    start_time=start,
                    end_time=end
                ).first()
                if not period:
                    period = LeaderboardPeriod(
                        leaderboard_type=timeframe_str,
                        start_time=start,
                        end_time=end,
                        is_active=True
                    )
                    session.add(period)
                    print(f"Creating new period: {start} to {end} CST")
                    session.commit()
                return period
        except Exception as e:
            raise Exception(str(e))

    async def get_total_game_hours_by_timeframe(self, timeframe: str) -> List[Tuple[str, float, str]]:
        """Get the total hours played for each game within a given timeframe."""
        session = self.Session()
        try:
            # Get current time in CST
            current_time = datetime.now(self.cst)
            start_time = None
            end_time = None

            if timeframe == 'weekly':
                # Start from last Monday 00:00 CST
                days_since_monday = current_time.weekday()
                start_time = (current_time - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_time = start_time + timedelta(days=7)
            elif timeframe == 'monthly':
                # Start from 1st of current month CST
                start_time = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if current_time.month == 12:
                    end_time = current_time.replace(year=current_time.year + 1, month=1, day=1)
                else:
                    end_time = current_time.replace(month=current_time.month + 1, day=1)
            elif timeframe == 'alltime':
                start_time = None
                end_time = None
            else:
                print(f"DEBUG: Invalid timeframe specified: {timeframe}")
                return []

            query = session.query(
                Game.name,
                func.sum(GamingSession.hours).label('total_hours'),
                Game.box_art_url
            ).join(Game, GamingSession.game_id == Game.id)

            if start_time:
                query = query.filter(GamingSession.timestamp >= start_time)
            if end_time:
                query = query.filter(GamingSession.timestamp < end_time)

            # Group by both game name and box_art_url
            query = query.group_by(Game.name, Game.box_art_url)
            query = query.order_by(text('total_hours DESC'))

            results = query.all()
            
            # Format results as list of tuples (game_name, total_hours, box_art_url)
            formatted_results = [(r.name, float(r.total_hours), r.box_art_url) for r in results]
            return formatted_results

        except Exception as e:
            print(f"ERROR: Error getting total game hours for timeframe {timeframe}: {str(e)}")
            print("Full traceback:")
            import traceback
            traceback.print_exc()
            return []
        finally:
            session.close()

    async def get_leaderboard_by_timeframe(self, timeframe: LeaderboardType, bot=None, period=None, custom_start=None, custom_end=None) -> List[Tuple[int, float, int, str, float, float]]:
        """Get leaderboard data for a specific timeframe. Optionally override period boundaries with custom_start/custom_end."""
        db_session = self.Session()
        try:
            # Calculate timeframe based on current time in CST or use custom boundaries
            if custom_start is not None and custom_end is not None:
                start_time = custom_start
                end_time = custom_end
            else:
                current_time = datetime.now(self.cst)
                start_time = None
                end_time = None

                if timeframe == LeaderboardType.WEEKLY:
                    days_since_monday = current_time.weekday()
                    start_time = (current_time - timedelta(days=days_since_monday)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    end_time = start_time + timedelta(days=7)
                elif timeframe == LeaderboardType.MONTHLY:
                    start_time = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    if current_time.month == 12:
                        end_time = current_time.replace(year=current_time.year + 1, month=1, day=1)
                    else:
                        end_time = current_time.replace(month=current_time.month + 1, day=1)
                else:  # ALLTIME
                    start_time = None
                    end_time = None

            # First, get the most played game for each user
            user_most_played = db_session.query(
                GamingSession.user_id,
                Game.name.label('game_name'),
                func.sum(GamingSession.hours).label('game_hours')
            ).join(
                Game, GamingSession.game_id == Game.id
            )

            if start_time:
                user_most_played = user_most_played.filter(GamingSession.timestamp >= start_time)
            if end_time:
                user_most_played = user_most_played.filter(GamingSession.timestamp < end_time)

            user_most_played = user_most_played.group_by(
                GamingSession.user_id,
                Game.name
            ).subquery()

            # Get the most played game for each user
            most_played_games = db_session.query(
                user_most_played.c.user_id,
                user_most_played.c.game_name,
                user_most_played.c.game_hours
            ).distinct(
                user_most_played.c.user_id
            ).order_by(
                user_most_played.c.user_id,
                user_most_played.c.game_hours.desc()
            ).subquery()

            # Get total hours for each user
            total_hours = db_session.query(
                GamingSession.user_id,
                func.sum(GamingSession.hours).label('total_hours')
            )

            if start_time:
                total_hours = total_hours.filter(GamingSession.timestamp >= start_time)
            if end_time:
                total_hours = total_hours.filter(GamingSession.timestamp < end_time)

            total_hours = total_hours.group_by(
                GamingSession.user_id
            ).subquery()

            # Get session credits for each user
            session_credits = db_session.query(
                GamingSession.user_id,
                func.sum(GamingSession.credits_earned).label('session_credits'),
                func.count(GamingSession.game_id.distinct()).label('games_played')
            )

            if start_time:
                session_credits = session_credits.filter(GamingSession.timestamp >= start_time)
            if end_time:
                session_credits = session_credits.filter(GamingSession.timestamp < end_time)

            session_credits = session_credits.group_by(
                GamingSession.user_id
            ).subquery()

            if timeframe == LeaderboardType.ALLTIME:
                # Get bonus credits for each user (only for all-time)
                bonus_credits = db_session.query(
                    Bonus.user_id,
                    func.sum(Bonus.credits).label('bonus_credits')
                ).group_by(
                    Bonus.user_id
                ).subquery()

                # Combine session and bonus credits for all-time
                results = db_session.query(
                    session_credits.c.user_id,
                    (func.coalesce(session_credits.c.session_credits, 0) + func.coalesce(bonus_credits.c.bonus_credits, 0)).label('total_credits'),
                    session_credits.c.games_played,
                    most_played_games.c.game_name,
                    most_played_games.c.game_hours,
                    total_hours.c.total_hours
                ).outerjoin(
                    most_played_games,
                    session_credits.c.user_id == most_played_games.c.user_id
                ).outerjoin(
                    total_hours,
                    session_credits.c.user_id == total_hours.c.user_id
                ).outerjoin(
                    bonus_credits,
                    session_credits.c.user_id == bonus_credits.c.user_id
                ).order_by(
                    (func.coalesce(session_credits.c.session_credits, 0) + func.coalesce(bonus_credits.c.bonus_credits, 0)).desc()
                ).all()
            else:
                # For weekly and monthly, only use session credits
                results = db_session.query(
                    session_credits.c.user_id,
                    session_credits.c.session_credits.label('total_credits'),
                    session_credits.c.games_played,
                    most_played_games.c.game_name,
                    most_played_games.c.game_hours,
                    total_hours.c.total_hours
                ).outerjoin(
                    most_played_games,
                    session_credits.c.user_id == most_played_games.c.user_id
                ).outerjoin(
                    total_hours,
                    session_credits.c.user_id == total_hours.c.user_id
                ).order_by(
                    session_credits.c.session_credits.desc()
                ).all()

            # Format the results
            leaderboard = []
            seen_users = set()  # Track users we've already added
            for user_id, credits, games, most_played_game, most_played_hours, total_hours in results:
                if user_id not in seen_users:  # Only add each user once
                    leaderboard.append((
                        user_id,
                        float(credits or 0),
                        int(games or 0),
                        most_played_game or 'No games',
                        float(most_played_hours or 0),
                        float(total_hours or 0)
                    ))
                    seen_users.add(user_id)

            return leaderboard

        except Exception as e:
            print(f"ERROR: Failed to get leaderboard data: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            return []
        finally:
            db_session.close()

    async def record_leaderboard_placements(self, leaderboard_type: LeaderboardType, placements: List[Tuple[int, float, int, str, float, float]], period: LeaderboardPeriod) -> None:
        """Record placements for the given leaderboard period. Always use unified period boundaries for recalculation."""
        session = self.Session()
        try:
            # Only allow updating the most recent inactive period or an active period
            most_recent_inactive = session.query(LeaderboardPeriod).filter(
                LeaderboardPeriod.leaderboard_type == leaderboard_type,
                LeaderboardPeriod.is_active == False
            ).order_by(LeaderboardPeriod.end_time.desc()).first()
            if not period.is_active and (not most_recent_inactive or period.id != most_recent_inactive.id):
                print(f"Refusing to update placements for period {period.id} (not the most recent inactive period). No changes made.")
                return
            # Use unified period boundary calculation
            from storage import get_period_boundaries
            period_type = period.leaderboard_type.value.lower()
            start, end = get_period_boundaries(period.start_time, period_type)
            # Recalculate leaderboard data for this period
            leaderboard_data = await self.get_leaderboard_by_timeframe(leaderboard_type, custom_start=start, custom_end=end)
            naive_now = datetime.now()
            current_time = self.cst.localize(naive_now)
            print(f"\nRecording placements for {leaderboard_type.value}:")
            print(f"Period: {start} to {end} CST")
            print(f"Number of placements: {len(leaderboard_data)}")
            existing_records = session.query(LeaderboardHistory)\
                .filter(LeaderboardHistory.period_id == period.id)\
                .all()
            if existing_records:
                print(f"Found {len(existing_records)} existing records for this period - updating")
                for record in existing_records:
                    session.delete(record)
                session.commit()
            for position, (user_id, credits, games, most_played, most_played_hours, total_hours) in enumerate(leaderboard_data, 1):
                history = LeaderboardHistory(
                    user_id=user_id,
                    period_id=period.id,
                    leaderboard_type=leaderboard_type,
                    placement=position,
                    credits=credits,
                    games_played=games,
                    most_played_game=most_played,
                    most_played_hours=most_played_hours,
                    total_hours=total_hours,
                    timestamp=current_time
                )
                session.add(history)
                print(f"Recording {position}{self._get_ordinal_suffix(position)} place: User {user_id} with {credits:,.1f} credits")
            session.commit()
            print("Successfully recorded all placements")
        except Exception as e:
            print(f"Error recording leaderboard history: {str(e)}")
            session.rollback()
        finally:
            session.close()

    def _get_ordinal_suffix(self, number: int) -> str:
        """Helper method to get ordinal suffix (st, nd, rd, th)"""
        if 10 <= number % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
        return suffix

    def get_user_placement_history(self, user_id: str, leaderboard_type: Optional[LeaderboardType] = None) -> List[Dict]:
        """Get user's leaderboard placement history"""
        session = self.Session()
        try:
            # Convert user_id to integer for database query
            user_id_int = int(user_id)
            
            query = session.query(LeaderboardHistory)\
                .filter(LeaderboardHistory.user_id == user_id_int)

            if leaderboard_type:
                query = query.filter(LeaderboardHistory.leaderboard_type == leaderboard_type)

            history = query.order_by(LeaderboardHistory.period_id.desc()).all()

            return [{
                'period_id': h.period_id,
                'leaderboard_type': h.leaderboard_type.value,
                'placement': h.placement,
                'credits': float(h.credits),
                'games_played': h.games_played,
                'most_played_game': h.most_played_game,
                'most_played_hours': float(h.most_played_hours),
                'start_time': h.period.start_time.isoformat(),
                'end_time': h.period.end_time.isoformat()
            } for h in history]
        finally:
            session.close()

    def get_user_gaming_history(self, user_id: str, limit: int = None) -> List[Dict]:
        """Get user's gaming history (all sessions)"""
        session = self.Session()
        try:
            # Get all sessions with game info in a single query
            sql = """
                SELECT 
                    g.name as game,
                    gs.hours,
                    gs.credits_earned,
                    g.credits_per_hour as rate,
                    gs.timestamp,
                    gs.players
                FROM gaming_sessions gs
                JOIN games g ON g.id = gs.game_id
                WHERE gs.user_id = :user_id
                ORDER BY gs.timestamp DESC
            """
            params = {"user_id": user_id}
            if limit:
                sql += " LIMIT :limit"
                params["limit"] = limit
            results = session.execute(text(sql), params).fetchall()

            return [{
                "game": row.game,
                "hours": float(row.hours),
                "credits_earned": float(row.credits_earned),
                "rate": float(row.rate),
                "timestamp": row.timestamp,
                "players": row.players
            } for row in results]
        finally:
            session.close()

    def get_user_achievements(self, user_id: str) -> Dict[str, bool]:
        """Get user's achievement status"""
        session = self.Session()
        try:
            # Get total stats
            total_credits = self.get_user_credits(user_id)
            total_hours = session.query(func.sum(GamingSession.hours))\
                .filter(GamingSession.user_id == user_id)\
                .scalar() or 0
            unique_games = session.query(func.count(GamingSession.game_id.distinct()))\
                .filter(GamingSession.user_id == user_id)\
                .scalar() or 0

            # Get longest session
            longest_session = session.query(func.max(GamingSession.hours))\
                .filter(GamingSession.user_id == user_id)\
                .scalar() or 0

            # Get highest rate game played
            highest_rate = session.query(func.max(Game.credits_per_hour))\
                .join(GamingSession)\
                .filter(GamingSession.user_id == user_id)\
                .scalar() or 0

            # Get number of games with more than 10 hours
            dedicated_games = session.query(func.count(GamingSession.game_id.distinct()))\
                .filter(GamingSession.user_id == user_id)\
                .group_by(GamingSession.game_id)\
                .having(func.sum(GamingSession.hours) >= 10)\
                .count()

            return {
                # Time-based achievements
                'novice_gamer': total_hours >= 10,
                'veteran_gamer': total_hours >= 100,
                'gaming_legend': total_hours >= 1000,
                'gaming_god': total_hours >= 5000,

                # Credit-based achievements
                'credit_starter': total_credits >= 10,
                'credit_collector': total_credits >= 100,
                'credit_hoarder': total_credits >= 1000,
                'credit_baron': total_credits >= 10000,
                'credit_millionaire': total_credits >= 1000000,

                # Game variety achievements
                'game_curious': unique_games >= 3,
                'game_explorer': unique_games >= 5,
                'game_adventurer': unique_games >= 10,
                'game_connoisseur': unique_games >= 20,
                'game_master': unique_games >= 50,

                # Session-based achievements
                'gaming_sprint': longest_session >= 1,
                'gaming_marathon': longest_session >= 5,
                'gaming_ultramarathon': longest_session >= 12,
                'gaming_immortal': longest_session >= 24,

                # Rate-based achievements
                'efficient_gamer': highest_rate >= 2,
                'pro_gamer': highest_rate >= 5,
                'elite_gamer': highest_rate >= 10,
                'legendary_gamer': highest_rate >= 100,

                # Dedication achievements
                'game_enthusiast': dedicated_games >= 1,
                'game_devotee': dedicated_games >= 3,
                'game_zealot': dedicated_games >= 5,
                'game_fanatic': dedicated_games >= 10
            }
        finally:
            session.close()

    async def set_game_credits_per_hour(self, game_name: str, credits: float, user_id: int) -> bool:
        """Set credits per hour for a game"""
        session = self.Session()
        try:
            # Format the game name
            formatted_name = ' '.join(word.capitalize() for word in game_name.split())
            
            # Get existing game
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(formatted_name)).first()
            
            if game:
                # Update existing game
                game.credits_per_hour = credits
                game.added_by = user_id
                
                # Force fetch and update RAWG data for existing games
                try:
                    print(f"Force fetching RAWG data for existing game: {game.name}")
                    rawg_data = await self.fetch_game_details_from_rawg(game.name)
                    if rawg_data:
                        # Force update all RAWG-related fields
                        game.rawg_id = rawg_data.get('rawg_id')
                        game.box_art_url = rawg_data.get('box_art_url')
                        game.release_date = rawg_data.get('release_date')
                        game.description = rawg_data.get('description')
                        print(f"Successfully force updated RAWG data for existing game: {game.name}")
                        print(f"- RAWG ID: {game.rawg_id}")
                        print(f"- Box art URL: {game.box_art_url}")
                        print(f"- Release date: {game.release_date}")
                        print(f"- Description: {len(game.description) if game.description else 0} chars")
                    else:
                        print(f"Failed to fetch RAWG data for existing game: {game.name}")
                except Exception as e:
                    print(f"Error fetching RAWG data for existing game {game.name}: {str(e)}")
                    print("Full traceback:")
                    traceback.print_exc()
                
                # Update all existing gaming sessions for this game
                gaming_sessions = session.query(GamingSession).filter(GamingSession.game_id == game.id).all()
                for gaming_session in gaming_sessions:
                    # Recalculate credits based on hours and new CPH
                    gaming_session.credits_earned = gaming_session.hours * credits
            else:
                # Create the Backloggd URL
                url_name = formatted_name.lower()
                url_name = url_name.replace("'", "").replace('"', "")
                url_name = ''.join(c if c.isalnum() else '-' for c in url_name)
                url_name = '-'.join(filter(None, url_name.split('-')))
                
                backloggd_url = f"https://www.backloggd.com/games/{url_name}/"
                
                # Fetch RAWG data
                rawg_data = None
                try:
                    print(f"Fetching RAWG data for new game: {formatted_name}")
                    rawg_data = await self.fetch_game_details_from_rawg(formatted_name)
                    if rawg_data:
                        print(f"Successfully fetched RAWG data for new game: {formatted_name}")
                        print(f"- RAWG ID: {rawg_data.get('rawg_id')}")
                        print(f"- Box art URL: {rawg_data.get('box_art_url')}")
                        print(f"- Release date: {rawg_data.get('release_date')}")
                    else:
                        print(f"Failed to fetch RAWG data for new game: {formatted_name}")
                except Exception as e:
                    print(f"Error fetching RAWG data for new game {formatted_name}: {str(e)}")
                    print("Full traceback:")
                    traceback.print_exc()
                
                # Create new game with all data
                game = Game(
                    name=formatted_name, 
                    credits_per_hour=credits, 
                    added_by=user_id,
                    backloggd_url=backloggd_url,
                    rawg_id=rawg_data.get('rawg_id') if rawg_data else None,
                    box_art_url=rawg_data.get('box_art_url') if rawg_data else None,
                    release_date=rawg_data.get('release_date') if rawg_data else None,
                    description=rawg_data.get('description') if rawg_data else None
                )
                
                session.add(game)
            
            session.commit()
            return True

        except Exception as e:
            session.rollback()
            print(f"Error setting game credits per hour: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            return False
        finally:
            session.close()

    def _check_and_update_credits(self, session) -> bool:
        """Check if any game rates have changed in the database and update credits if needed"""
        try:
            # Force a new session to ensure we get fresh data
            temp_session = self.Session()
            try:
                # Get all games and their current rates from the database
                current_games = temp_session.query(Game.id, Game.credits_per_hour).all()
                current_rates = {game.id: game.credits_per_hour for game in current_games}

                # Check if we need to recalculate by comparing with stored sessions
                needs_update = False
                sessions = temp_session.query(
                    GamingSession.game_id,
                    GamingSession.hours,
                    GamingSession.credits_earned
                ).all()

                for session_data in sessions:
                    expected_credits = session_data.hours * current_rates.get(session_data.game_id, 1.0)
                    if abs(session_data.credits_earned - expected_credits) > 0.001:
                        needs_update = True
                        break
            finally:
                temp_session.close()

            # If we found any discrepancies, recalculate everything using a new session
            if needs_update:
                self.recalculate_all_credits()
                # Refresh the provided session to see the updates
                session.expire_all()
                session.commit()
                return True

            return False
        except Exception as e:
            return False

    def recalculate_all_credits(self) -> None:
        """Recalculate all credits based on current game rates and half-life settings"""
        session = self.Session()
        try:
            # Force refresh of all data
            session.expire_all()

            # Get all games and their current rates
            games_dict = {}
            for game in session.query(Game).all():
                games_dict[game.id] = game

            # Update all gaming sessions
            total_sessions = 0
            updated_sessions = 0

            for game_id, game in games_dict.items():
                # Get all sessions for this game
                sessions = session.query(GamingSession).filter(GamingSession.game_id == game_id).all()
                total_sessions += len(sessions)

                for gaming_session in sessions:
                    # Calculate new credits based on current rate and half-life
                    new_credits = self.calculate_credits_with_half_life(
                        gaming_session.hours, 
                        game.credits_per_hour, 
                        game.half_life_hours
                    )

                    # Update credits regardless of whether they've changed
                    gaming_session.credits_earned = new_credits
                    updated_sessions += 1

            session.commit()

            # Now recalculate all user totals based on their sessions
            self.recalculate_all_user_credits()

        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def update_user_total_credits(self, user_id: str) -> float:
        """Calculate and update user's total credits from their gaming sessions"""
        session = self.Session()
        try:
            # Calculate total credits from all gaming sessions
            session_credits = session.query(func.sum(GamingSession.credits_earned))\
                .filter(GamingSession.user_id == user_id)\
                .scalar() or 0.0

            # Calculate total credits from bonuses
            bonus_credits = session.query(func.sum(Bonus.credits))\
                .filter(Bonus.user_id == user_id)\
                .scalar() or 0.0
            
            # Total credits is sum of both
            total_credits = session_credits + bonus_credits

            # Update user stats
            user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
            if not user_stats:
                user_stats = UserStats(user_id=user_id, total_credits=total_credits)
                session.add(user_stats)
            else:
                user_stats.total_credits = total_credits

            session.commit()
            return total_credits
        finally:
            session.close()

    def recalculate_all_user_credits(self) -> None:
        """Recalculate all users' total credits from their gaming sessions"""
        session = self.Session()
        try:
            # Get all unique user IDs from gaming sessions
            user_ids = session.query(GamingSession.user_id.distinct()).all()

            for (user_id,) in user_ids:
                # Calculate total credits for this user
                session_credits = session.query(func.sum(GamingSession.credits_earned))\
                    .filter(GamingSession.user_id == user_id)\
                    .scalar() or 0.0
            
                 # Calculate total from bonuses
                bonus_credits = session.query(func.sum(Bonus.credits))\
                    .filter(Bonus.user_id == user_id)\
                    .scalar() or 0.0
                
                 # Total credits is sum of both
                total_credits = session_credits + bonus_credits

                # Update or create user stats
                user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
                if not user_stats:
                    user_stats = UserStats(user_id=user_id, total_credits=total_credits)
                    session.add(user_stats)

            session.commit()

        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    async def add_gaming_hours(self, user_id: int, hours: float, game_name: str) -> float:
        """Add gaming hours for a user and return the credits earned"""
        session = None
        try:
            session = self.get_session()
            
            # Check if the game exists (no auto-creation for Discord bot)
            formatted_name = ' '.join(word.capitalize() for word in game_name.split())
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(formatted_name)).first()
            
            if not game:
                raise Exception(f"Game '{game_name}' does not exist in the database. Please use `!setrate <credits> {game_name}` to add it first.")
            
            # Get user's total hours for this game (before this session)
            total_game_hours = session.query(func.sum(GamingSession.hours))\
                .filter(GamingSession.user_id == user_id, GamingSession.game_id == game.id)\
                .scalar() or 0.0
            
            # Calculate credits earned with half-life system based on total accumulated hours
            credits_earned = self.calculate_credits_with_half_life_for_session(
                hours, 
                total_game_hours, 
                game.credits_per_hour, 
                game.half_life_hours
            )
            
            # Create or update gaming session
            gaming_session = GamingSession(
                user_id=user_id,
                game_id=game.id,
                hours=hours,
                credits_earned=credits_earned,
                timestamp=datetime.now(timezone.utc)
            )
            session.add(gaming_session)
            
            # Update user stats
            user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
            if not user_stats:
                user_stats = UserStats(user_id=user_id)
                session.add(user_stats)
            
            user_stats.total_credits += credits_earned
            
            # Commit changes
            session.commit()
            
            return credits_earned
            
        except Exception as e:
            if session:
                session.rollback()
            print(f"Error adding gaming hours: {str(e)}")
            print("Full error details:", file=sys.stderr)
            traceback.print_exc()
            raise
        finally:
            if session:
                session.close()

    def get_user_credits(self, user_id: int) -> float:
        """Get user's total credits by summing all gaming sessions and bonuses"""
        session = self.Session()
        try:
            # Calculate total from gaming sessions
            session_credits = session.query(func.sum(GamingSession.credits_earned))\
                .filter(GamingSession.user_id == user_id)\
                .scalar() or 0.0
                
            # Calculate total from bonuses
            bonus_credits = session.query(func.sum(Bonus.credits))\
                .filter(Bonus.user_id == user_id)\
                .scalar() or 0.0

            # Total credits is sum of both
            total_credits = session_credits + bonus_credits

            # Update the stored total in user_stats to keep it in sync
            user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
            if user_stats and abs(user_stats.total_credits - total_credits) > 0.001:
                user_stats.total_credits = total_credits
                session.commit()

            return total_credits
        finally:
            session.close()

    def get_leaderboard(self) -> List[Tuple[int, float]]:
        """Get sorted list of (user_id, credits) tuples"""
        session = self.Session()
        try:
            # Get total credits from gaming sessions for each user
            session_credits = session.query(
                GamingSession.user_id,
                func.sum(GamingSession.credits_earned).label('session_credits')
            ).group_by(
                GamingSession.user_id
            ).subquery()

            # Get total bonus credits for each user
            bonus_credits = session.query(
                Bonus.user_id,
                func.sum(Bonus.credits).label('bonus_credits')
            ).group_by(
                Bonus.user_id
            ).subquery()

            # Combine session credits and bonus credits
            results = session.query(
                session_credits.c.user_id,
                (func.coalesce(session_credits.c.session_credits, 0) + func.coalesce(bonus_credits.c.bonus_credits, 0)).label('total_credits')
            ).outerjoin(
                bonus_credits,
                session_credits.c.user_id == bonus_credits.c.user_id
            ).all()

            # Update user_stats table with new total credits
            for user_id, total_credits in results:
                user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
                if user_stats:
                    user_stats.total_credits = total_credits
                else:
                    user_stats = UserStats(user_id=user_id, total_credits=total_credits)
                    session.add(user_stats)
            
            session.commit()

            # Get all users ordered by total credits
            users = session.query(UserStats)\
                .order_by(UserStats.total_credits.desc())\
                .all()
            
            # Return list of (user_id, total_credits) tuples
            return [(user.user_id, user.total_credits) for user in users]
        finally:
            session.close()

    def get_game_info(self, game_name: str) -> Optional[Dict]:
        """Get basic information about a game"""
        session = self.Session()
        try:
            # Get game info without joining users table
            result = session.execute(text("""
                SELECT 
                    g.*
                FROM games g
                WHERE LOWER(g.name) = LOWER(:game_name)
            """), {"game_name": game_name}).first()

            if not result:
                return None

            return {
                "name": result.name,
                "credits_per_hour": float(result.credits_per_hour),
                "half_life_hours": float(result.half_life_hours) if result.half_life_hours else None,
                "added_by": result.added_by,
                "backloggd_url": result.backloggd_url
            }
        finally:
            session.close()

    def get_user_overall_stats(self, user_id: str) -> Dict[str, Any]:
        """Get overall gaming statistics for a user"""
        session = self.Session()
        try:
            # Get all stats in a single query
            result = session.execute(text("""
                WITH user_stats AS (
                    SELECT 
                        COALESCE(SUM(hours), 0) as total_hours,
                        COALESCE(SUM(credits_earned), 0) as session_credits,
                        COUNT(DISTINCT game_id) as games_played,
                        COUNT(*) as total_sessions,
                        MIN(timestamp) as first_played,
                        MAX(timestamp) as last_played
                    FROM gaming_sessions
                    WHERE user_id = :user_id
                ),
                bonus_stats AS (
                    SELECT 
                        COALESCE(SUM(credits), 0) as bonus_credits
                    FROM bonuses
                    WHERE user_id = :user_id
                ),
                most_played AS (
                    SELECT 
                        g.name,
                        SUM(gs.hours) as total_hours
                    FROM gaming_sessions gs
                    JOIN games g ON g.id = gs.game_id
                    WHERE gs.user_id = :user_id
                    GROUP BY g.id, g.name
                    ORDER BY total_hours DESC
                    LIMIT 1
                ),
                user_rank AS (
                    SELECT 
                        user_id,
                        RANK() OVER (ORDER BY (COALESCE(SUM(credits_earned), 0) + COALESCE(SUM(bonus_credits), 0)) DESC) as rank
                    FROM (
                        SELECT 
                            gs.user_id,
                            gs.credits_earned,
                            0 as bonus_credits
                        FROM gaming_sessions gs
                        UNION ALL
                        SELECT 
                            b.user_id,
                            0 as credits_earned,
                            b.credits as bonus_credits
                        FROM bonuses b
                    ) combined_credits
                    GROUP BY user_id
                )
                SELECT 
                    us.total_hours,
                    (us.session_credits + COALESCE(bs.bonus_credits, 0)) as total_credits,
                    us.games_played,
                    us.total_sessions,
                    us.first_played,
                    us.last_played,
                    mp.name as most_played_game,
                    mp.total_hours as most_played_hours,
                    ur.rank
                FROM user_stats us
                LEFT JOIN bonus_stats bs ON true
                LEFT JOIN most_played mp ON true
                LEFT JOIN user_rank ur ON ur.user_id = :user_id
            """), {"user_id": user_id}).first()

            if not result:
                return {
                    "total_hours": 0,
                    "total_credits": 0,
                    "games_played": 0,
                    "total_sessions": 0,
                    "first_played": None,
                    "last_played": None,
                    "most_played_game": None,
                    "most_played_hours": 0,
                    "rank": None
                }

            return {
                "total_hours": float(result.total_hours),
                "total_credits": float(result.total_credits),
                "games_played": result.games_played,
                "total_sessions": result.total_sessions,
                "first_played": result.first_played,
                "last_played": result.last_played,
                "most_played_game": result.most_played_game,
                "most_played_hours": float(result.most_played_hours) if result.most_played_hours else 0,
                "rank": result.rank
            }
        finally:
            session.close()

    def get_game_stats(self, game_name: str) -> Optional[Dict]:
        """Get overall statistics for a game"""
        session = self.Session()
        try:
            # Get game info
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(game_name)).first()
            if not game:
                return None

            # Get game stats
            result = session.execute(text("""
                SELECT 
                    COALESCE(SUM(hours), 0) as total_hours,
                    COALESCE(SUM(credits_earned), 0) as total_credits,
                    COUNT(*) as total_sessions,
                    COUNT(DISTINCT user_id) as unique_players
                FROM gaming_sessions
                WHERE game_id = :game_id
            """), {"game_id": game.id}).first()

            if not result:
                return None

            return {
                "name": game.name,
                "total_hours": float(result.total_hours),
                "total_credits": float(result.total_credits),
                "total_sessions": result.total_sessions,
                "unique_players": result.unique_players,
                "credits_per_hour": game.credits_per_hour,
                "half_life_hours": game.half_life_hours,
                "added_by": game.added_by,
                "backloggd_url": game.backloggd_url,
                "box_art_url": game.box_art_url,
                "rawg_id": game.rawg_id,
                "release_date": game.release_date,
                "description": game.description
            }
        finally:
            session.close()

    def get_user_game_summaries(self, user_id: str) -> List[Dict]:
        """Get summaries of all games played by a user"""
        session = self.Session()
        try:
            results = session.execute(text("""
                SELECT 
                    g.name,
                    COALESCE(SUM(gs.hours), 0) as total_hours,
                    COALESCE(SUM(gs.credits_earned), 0) as total_credits,
                    COUNT(*) as sessions,
                    MIN(gs.timestamp) as first_played,
                    MAX(gs.timestamp) as last_played
                FROM gaming_sessions gs
                JOIN games g ON g.id = gs.game_id
                WHERE gs.user_id = :user_id
                GROUP BY g.id, g.name
                ORDER BY total_hours DESC
            """), {"user_id": user_id}).fetchall()

            return [{
                "game": row.name,
                "total_hours": float(row.total_hours),
                "total_credits": float(row.total_credits),
                "sessions": row.sessions,
                "first_played": row.first_played,
                "last_played": row.last_played
            } for row in results]
        finally:
            session.close()

    def get_user_game_stats(self, user_id: str, game_name: str) -> Optional[Dict]:
        """Get game-specific statistics for a user"""
        session = self.Session()
        try:
            # Get game info
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(game_name)).first()
            if not game:
                return None

            # Get user's stats for this game
            result = session.execute(text("""
                SELECT 
                    COALESCE(SUM(hours), 0) as total_hours,
                    COALESCE(SUM(credits_earned), 0) as total_credits,
                    COUNT(*) as total_sessions,
                    MIN(timestamp) as first_played,
                    MAX(timestamp) as last_played
                FROM gaming_sessions
                WHERE user_id = :user_id AND game_id = :game_id
            """), {
                "user_id": user_id,
                "game_id": game.id
            }).first()

            if not result:
                return None

            return {
                "name": game.name,
                "total_hours": float(result.total_hours),
                "total_credits": float(result.total_credits),
                "total_sessions": result.total_sessions,
                "first_played": result.first_played,
                "last_played": result.last_played,
                "credits_per_hour": game.credits_per_hour,
                "backloggd_url": game.backloggd_url
            }
        finally:
            session.close()

    def add_bonus_credits(self, user_id: int, credits: float, reason: str, granted_by: int) -> float:
        """Add bonus credits to a user's balance and log the bonus"""
        session = self.Session()
        try:
            # Get or create user stats
            user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
            if not user_stats:
                user_stats = UserStats(user_id=user_id, total_credits=0.0)
                session.add(user_stats)
                session.commit()

            # Add the bonus credits
            user_stats.total_credits += credits

            # Log the bonus
            bonus = Bonus(
                user_id=user_id,
                credits=credits,
                reason=reason,
                granted_by=granted_by,
                timestamp=datetime.now(pytz.UTC)
            )
            session.add(bonus)
            session.commit()
            return user_stats.total_credits

        finally:
            session.close()

    def rename_game(self, old_name: str, new_name: str, user_id: int) -> Optional[Dict]:
        """Rename a game in the database"""
        session = self.Session()
        try:
            # Check if the old game exists
            old_game = session.query(Game).filter(func.lower(Game.name) == func.lower(old_name)).first()
            if not old_game:
                return None

            # Check if the new name already exists (case insensitive)
            existing_game = session.query(Game).filter(
                func.lower(Game.name) == func.lower(new_name)
            ).first()
            if existing_game and existing_game.id != old_game.id:
                return None

            # Store old info for return value
            old_info = {
                'old_name': old_game.name,
                'new_name': new_name,
                'credits_per_hour': old_game.credits_per_hour,
                'added_by': old_game.added_by
            }

            # Update the game name
            old_game.name = new_name.strip().capitalize()
            session.commit()

            return old_info
        finally:
            session.close()

    def delete_game(self, game_name: str) -> Optional[Dict]:
        """Delete a game from the database and return its stats"""
        session = self.Session()
        try:
            # Get game and its stats before deletion
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(game_name)).first()
            if not game:
                return None

            # Get game stats before deletion
            stats = session.query(
                func.sum(GamingSession.hours).label('total_hours'),
                func.sum(GamingSession.credits_earned).label('total_credits'),
                func.count(GamingSession.id.distinct()).label('total_sessions'),
                func.count(GamingSession.user_id.distinct()).label('unique_players')
            ).filter(GamingSession.game_id == game.id).first()

            # Store stats for return value
            game_info = {
                'name': game.name,
                'credits_per_hour': game.credits_per_hour,
                'added_by': game.added_by,
                'total_hours': float(stats.total_hours or 0),
                'total_credits': float(stats.total_credits or 0),
                'total_sessions': stats.total_sessions,
                'unique_players': stats.unique_players
            }

            # Delete all gaming sessions for this game first
            session.query(GamingSession).filter(GamingSession.game_id == game.id).delete()

            # Then delete the game itself
            session.delete(game)
            session.commit()

            return game_info
        finally:
            session.close()

    def set_game_backloggd_url(self, game_name: str, url: str) -> bool:
        """Set the Backloggd URL for a game"""
        session = self.Session()
        try:
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(game_name)).first()
            if game:
                game.backloggd_url = url
                session.commit()
                return True
            return False
        finally:
            session.close()

    async def get_recent_gaming_sessions(self, limit: int = 20, timeframe: str = 'alltime') -> List[Dict[str, Any]]:
        """Get the most recent gaming sessions with game details, filtered by timeframe (weekly, monthly, alltime)."""
        session = self.Session()
        try:
            # Calculate timeframe boundaries in CST
            now = datetime.now(self.cst)
            start_time = None
            end_time = now
            if timeframe == 'weekly':
                days_since_monday = now.weekday()
                start_time = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif timeframe == 'monthly':
                start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # For alltime, start_time remains None

            # Fetch recent gaming sessions with game details
            sessions_query = session.query(
                GamingSession.id,
                GamingSession.user_id,
                GamingSession.game_id,
                GamingSession.hours,
                GamingSession.timestamp,
                GamingSession.players,
                Game.name.label('game_name'),
                Game.box_art_url
            ).join(Game, GamingSession.game_id == Game.id, isouter=True)

            if start_time:
                sessions_query = sessions_query.filter(GamingSession.timestamp >= start_time)
            if end_time:
                sessions_query = sessions_query.filter(GamingSession.timestamp <= end_time)

            sessions_query = sessions_query.order_by(GamingSession.timestamp.desc()).limit(limit)

            rows = sessions_query.all()

            if not rows:
                return []

            sessions_data = []
            for row in rows:
                box_art_url = row.box_art_url
                # If no box art URL, try to fetch from RAWG
                if not box_art_url:
                    rawg_data = await self.fetch_game_details_from_rawg(row.game_name)
                    if rawg_data and rawg_data.get('box_art_url'):
                        box_art_url = rawg_data['box_art_url']
                        # Update the game in the database with the RAWG box art URL
                        game = session.query(Game).filter(Game.id == row.game_id).first()
                        if game:
                            game.box_art_url = box_art_url
                            session.commit()

                sessions_data.append({
                    'id': row.id,
                    'user_id': str(row.user_id),
                    'game_id': row.game_id,
                    'hours': row.hours,
                    'timestamp': row.timestamp,
                    'players': row.players,
                    'game_name': row.game_name or f'Game{row.game_id}',
                    'box_art_url': box_art_url
                })

            return sessions_data

        except Exception as e:
            print(f"Error getting recent gaming sessions: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            session.close()

    async def get_recent_bonuses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent bonus entries with user details."""
        session = self.Session()
        try:
            # Fetch recent bonus entries
            bonuses_query = session.query(
                Bonus.id,
                Bonus.user_id,
                Bonus.credits,
                Bonus.reason,
                Bonus.granted_by,
                Bonus.timestamp
            ).order_by(Bonus.timestamp.desc())\
             .limit(limit)

            rows = bonuses_query.all()

            # Format the results as a list of dictionaries
            recent_bonuses = []
            for row in rows:
                # Convert row to dictionary, ensuring user IDs are strings
                bonus_data = {
                    'id': row.id,
                    'user_id': str(row.user_id),  # Convert to string to preserve precision
                    'credits': row.credits,
                    'reason': row.reason,
                    'granted_by': str(row.granted_by),  # Convert to string to preserve precision
                    'timestamp': row.timestamp
                }
                recent_bonuses.append(bonus_data)

            # If no real bonuses, return empty list (frontend handles display)
            if not recent_bonuses:
                return []

            return recent_bonuses

        except Exception as e:
            print(f"Error getting recent bonuses: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            session.close()

    async def get_user_most_played_game_by_timeframe(self, user_id: str, timeframe: str, limit: int = 1) -> List[Dict[str, Any]]:
        """Get the user's most played game(s) and hours for a given timeframe, up to a specified limit."""
        session = self.Session()
        try:
            # Get current time in UTC first
            utc_now = datetime.now(pytz.UTC)
            # Convert to CST
            now = utc_now.astimezone(self.cst)
            print(f"\nGetting most played games for user {user_id} in {timeframe} timeframe:")
            print(f"UTC time: {utc_now}")
            print(f"CST time: {now}")

            start_time = None
            end_time = now # End time is always now for current period calculations

            if timeframe == 'weekly':
                # Start from last Monday 00:00 CST
                days_since_monday = now.weekday()
                start_time = (now - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                print(f"Weekly start time: {start_time}")
            elif timeframe == 'monthly':
                # Start from 1st of current month CST
                start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                print(f"Monthly start time: {start_time}")
            elif timeframe == 'alltime':
                # No start time limit for all-time
                start_time = None # Set start_time to None for all-time
                print("All-time timeframe - no start time limit")
            else:
                # Invalid timeframe
                print(f"Error: Invalid timeframe provided to get_user_most_played_game_by_timeframe: {timeframe}")
                return []

            # Query for gaming sessions within the timeframe for the specific user
            query = session.query(
                Game.name,
                Game.box_art_url,
                func.sum(GamingSession.hours).label('total_hours')
            ).join(Game, GamingSession.game_id == Game.id)\
             .filter(GamingSession.user_id == user_id)

            # Apply timeframe filtering
            if start_time:
                print(f"Filtering sessions after: {start_time}")
                query = query.filter(GamingSession.timestamp >= start_time)

            query = query.group_by(Game.id, Game.name, Game.box_art_url)\
                         .order_by(func.sum(GamingSession.hours).desc())\
                         .limit(limit)

            results = query.all()
            print(f"Found {len(results)} games for user {user_id}")

            # Format the results as a list of dictionaries
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'game_name': result.name,
                    'total_hours': float(result.total_hours),
                    'box_art_url': result.box_art_url
                })
                print(f"Game: {result.name}, Hours: {result.total_hours}")

            return formatted_results # Return a list of dictionaries

        except Exception as e:
            print(f"Error in get_user_most_played_game_by_timeframe for user {user_id}, timeframe {timeframe}: {e}")
            print("Full traceback:")
            traceback.print_exc()
            return []
        finally:
            session.close()

    def get_recent_players_for_game(self, game_name: str, timeframe: str = 'alltime', limit: int = 10) -> List[Dict[str, Any]]:
        """Get a list of users who recently played a specific game."""
        session = self.Session()
        try:
            # Start with a base query on GamingSession, joined with Game
            base_query = session.query(GamingSession)\
                .join(Game, GamingSession.game_id == Game.id)\
                .filter(
                    func.lower(Game.name) == func.lower(game_name)
                )

            # Add timeframe filtering if specified
            if timeframe == 'weekly':
                # Calculate the start of the week (last 7 days from now in CST)
                now_cst = datetime.now(self.cst)
                start_of_week = now_cst - timedelta(days=7)
                base_query = base_query.filter(
                    GamingSession.timestamp >= start_of_week
                )

            # Subquery to find the latest session timestamp and total hours for each user within the filtered sessions
            subquery = base_query.with_entities(
                GamingSession.user_id,
                func.max(GamingSession.timestamp).label('latest_session_timestamp'),
                func.sum(GamingSession.hours).label('total_hours')
            ).group_by(GamingSession.user_id).subquery()

            # Final query to select user_id and total_hours, ordered by latest session timestamp
            query = session.query(
                subquery.c.user_id,
                subquery.c.total_hours
            ).select_from(subquery)\
            .order_by(subquery.c.latest_session_timestamp.desc())\
            .limit(limit)

            results = query.all()

            # Format results
            return [{
                'user_id': str(p.user_id), # Ensure user_id is a string
                'hours': float(p.total_hours)
            } for p in results]

        except Exception as e:
            print(f"Error getting recent players for game {game_name}: {e}")
            return []
        finally:
            session.close()

    def get_recent_activity_for_game(self, game_name: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Get the most recent gaming sessions for a specific game."""
        session = self.Session()
        try:
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(game_name)).first()
            if not game:
                return []

            # Fetch recent gaming sessions for this game
            sessions_query = session.query(
                GamingSession.id,
                GamingSession.user_id,
                GamingSession.hours,
                GamingSession.timestamp,
                Game.box_art_url, # Include box_art_url here
                Game.name.label('game_name') # Include game name here
            ).join(Game, GamingSession.game_id == Game.id)\
             .filter(GamingSession.game_id == game.id)\
             .order_by(GamingSession.timestamp.desc())\
             .limit(limit)

            rows = sessions_query.all()

            sessions_data = []
            for row in rows:
                sessions_data.append({
                    'id': row.id,
                    'user_id': str(row.user_id),  # Convert user_id to string to preserve precision
                    'hours': float(row.hours),
                    'timestamp': row.timestamp,
                    'game_name': row.game_name,
                    'box_art_url': row.box_art_url
                })

            return sessions_data

        except Exception as e:
            print(f"Error getting recent activity for game {game_name}: {str(e)}")
            return []
        finally:
            session.close()

    def get_multiple_game_stats(self, game_names):
        session = self.Session()
        try:
            games = session.query(Game).filter(Game.name.in_(game_names)).all()
            return {game.name: {
                'box_art_url': game.box_art_url,
                # add any other fields you need
            } for game in games}
        finally:
            session.close()

    def search_games_by_name(self, query, limit=8):
        session = self.Session()
        try:
            games = session.query(Game).filter(Game.name.ilike(f"%{query}%")).limit(limit).all()
            return [{
                'name': game.name,
                'box_art_url': game.box_art_url,
                'id': game.id
            } for game in games]
        finally:
            session.close()

    def search_users_by_name(self, query, limit=8):
        session = self.Session()
        try:
            users = session.query(UserStats).filter(UserStats.username.ilike(f"%{query}%")).limit(limit).all()
            return [{
                'user_id': str(user.user_id),  # Convert BigInteger to string
                'username': user.username,
                'avatar_url': user.avatar_url
            } for user in users]
        finally:
            session.close()

    def update_user_username(self, user_id, new_username):
        session = self.Session()
        try:
            user = session.query(UserStats).filter_by(user_id=user_id).first()
            if user and (not user.username or user.username != new_username):
                user.username = new_username
                session.commit()
        finally:
            session.close()

    def update_user_username_and_avatar(self, user_id, new_username, new_avatar_url):
        session = self.Session()
        try:
            user = session.query(UserStats).filter_by(user_id=user_id).first()
            updated = False
            if user:
                if not user.username or user.username != new_username:
                    user.username = new_username
                    updated = True
                if new_avatar_url and (not user.avatar_url or user.avatar_url != new_avatar_url):
                    user.avatar_url = new_avatar_url
                    updated = True
                if updated:
                    session.commit()
        finally:
            session.close()

    def calculate_credits_with_half_life(self, hours: float, base_cph: float, half_life_hours: float = None) -> float:
        """
        Calculate credits earned with half-life system.
        
        Args:
            hours: Total hours played
            base_cph: Base credits per hour
            half_life_hours: Hours after which CPH is halved (None means no half-life)
        
        Returns:
            Total credits earned
        """
        if half_life_hours is None or half_life_hours <= 0:
            # No half-life, use simple calculation
            return hours * base_cph
        
        total_credits = 0.0
        remaining_hours = hours
        current_cph = base_cph
        current_threshold = half_life_hours
        
        while remaining_hours > 0:
            # Calculate how many hours we can apply at the current CPH rate
            hours_at_current_rate = min(remaining_hours, current_threshold)
            
            # Add credits for this segment
            total_credits += hours_at_current_rate * current_cph
            
            # Update remaining hours
            remaining_hours -= hours_at_current_rate
            
            # If we still have hours remaining, halve the CPH and double the threshold
            if remaining_hours > 0:
                current_cph /= 2.0
                current_threshold *= 2.0
        
        return total_credits

    def calculate_credits_with_half_life_for_session(self, session_hours: float, total_game_hours: float, base_cph: float, half_life_hours: float = None) -> float:
        """
        Calculate credits earned for a new session with half-life system based on total accumulated hours.
        
        Args:
            session_hours: Hours for this specific session
            total_game_hours: Total hours already played on this game (before this session)
            base_cph: Base credits per hour
            half_life_hours: Hours after which CPH is halved (None means no half-life)
        
        Returns:
            Total credits earned for this session
        """
        if half_life_hours is None or half_life_hours <= 0:
            # No half-life, use simple calculation
            return session_hours * base_cph
        
        total_credits = 0.0
        remaining_session_hours = session_hours
        current_hour = total_game_hours  # Start from where we left off
        
        while remaining_session_hours > 0:
            # Calculate how many half-life boundaries have been crossed
            # At 0-10h: 0 boundaries crossed, CPH = base_cph
            # At 10-20h: 1 boundary crossed, CPH = base_cph/2
            # At 20-30h: 2 boundaries crossed, CPH = base_cph/4
            # etc.
            boundaries_crossed = int(current_hour // half_life_hours)
            current_cph = base_cph / (2 ** boundaries_crossed)
            
            # Calculate the next threshold
            next_threshold = (boundaries_crossed + 1) * half_life_hours
            
            # Calculate how many hours we can apply at the current CPH rate
            hours_until_next_threshold = next_threshold - current_hour
            hours_at_current_rate = min(remaining_session_hours, hours_until_next_threshold)
            
            # Add credits for this segment
            total_credits += hours_at_current_rate * current_cph
            
            # Update remaining hours and current hour
            remaining_session_hours -= hours_at_current_rate
            current_hour += hours_at_current_rate
        
        return total_credits

    def calculate_credits(self, duration_minutes: int) -> float:
        """Calculate credits earned for a given duration in minutes."""
        # Base rate is 1 credit per hour
        base_rate = 1.0
        hours = duration_minutes / 60.0
        return base_rate * hours

    def get_alltime_leaderboard(self) -> List[Tuple[int, float, int, str, float, float]]:
        """Get all-time leaderboard data."""
        db_session = self.Session()
        try:
            # Get total credits from gaming sessions for each user
            session_credits = db_session.query(
                GamingSession.user_id,
                func.sum(GamingSession.credits_earned).label('session_credits'),
                func.count(GamingSession.game_id.distinct()).label('games_played'),
                func.sum(GamingSession.hours).label('total_hours')
            ).group_by(
                GamingSession.user_id
            ).subquery()

            # Get total bonus credits for each user
            bonus_credits = db_session.query(
                Bonus.user_id,
                func.sum(Bonus.credits).label('bonus_credits')
            ).group_by(
                Bonus.user_id
            ).subquery()

            # Combine session credits and bonus credits
            results = db_session.query(
                session_credits.c.user_id,
                (func.coalesce(session_credits.c.session_credits, 0) + func.coalesce(bonus_credits.c.bonus_credits, 0)).label('total_credits'),
                session_credits.c.games_played,
                session_credits.c.total_hours
            ).outerjoin(
                bonus_credits,
                session_credits.c.user_id == bonus_credits.c.user_id
            ).order_by(
                (func.coalesce(session_credits.c.session_credits, 0) + func.coalesce(bonus_credits.c.bonus_credits, 0)).desc()
            ).all()

            # Get most played game for each user
            most_played_games = {}
            for user_id, _, _, _ in results:
                most_played = db_session.query(
                    Game.name,
                    func.sum(GamingSession.hours).label('game_hours')
                ).join(
                    GamingSession, Game.id == GamingSession.game_id
                ).filter(
                    GamingSession.user_id == user_id
                ).group_by(
                    Game.name
                ).order_by(
                    func.sum(GamingSession.hours).desc()
                ).first()

                if most_played:
                    most_played_games[user_id] = (most_played.name, float(most_played.game_hours))
                else:
                    most_played_games[user_id] = ('No games', 0.0)

            # Format the results
            leaderboard = []
            for user_id, total_credits, games_played, total_hours in results:
                most_played_game, most_played_hours = most_played_games.get(user_id, ('No games', 0.0))
                leaderboard.append((
                    user_id,
                    float(total_credits or 0),
                    int(games_played or 0),
                    most_played_game,
                    float(most_played_hours or 0),
                    float(total_hours or 0)
                ))

            return leaderboard

        except Exception as e:
            print(f"ERROR: Failed to get all-time leaderboard: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            raise
        finally:
            db_session.close()

    def get_all_games_with_stats(self) -> List[Dict[str, Any]]:
        """Get all games with their stats."""
        session = self.Session()
        try:
            # Query all games with their stats
            games_query = session.query(
                Game.id,
                Game.name,
                Game.box_art_url,
                Game.credits_per_hour,
                Game.half_life_hours,
                Game.backloggd_url,
                Game.release_date,  # Include release_date from database
                func.count(distinct(GamingSession.user_id)).label('unique_players'),
                func.sum(GamingSession.hours).label('total_hours')
            ).outerjoin(GamingSession, Game.id == GamingSession.game_id)\
             .group_by(Game.id)\
             .order_by(Game.name)

            rows = games_query.all()

            # Format the results
            games_data = []
            for row in rows:
                # Format the game name with proper capitalization
                name = row.name.strip()
                if name:
                    # First, capitalize the first letter of the entire string
                    name = name[0].upper() + name[1:]
                    
                    # Then capitalize each word, preserving Roman numerals
                    words = name.split()
                    formatted_words = []
                    for word in words:
                        # Check if the word is a Roman numeral (case-insensitive)
                        roman_numerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV']
                        if word.upper() in roman_numerals:
                            formatted_words.append(word.upper())
                        else:
                            formatted_words.append(word.capitalize())
                    
                    name = ' '.join(formatted_words)

                games_data.append({
                    'id': row.id,
                    'name': name,
                    'box_art_url': row.box_art_url,
                    'credits_per_hour': float(row.credits_per_hour),
                    'half_life_hours': float(row.half_life_hours) if row.half_life_hours else None,
                    'backloggd_url': row.backloggd_url,
                    'unique_players': row.unique_players or 0,
                    'total_hours': float(row.total_hours or 0),
                    'release_date': row.release_date  # Use release_date from database
                })

            return games_data

        except Exception as e:
            print(f"Error getting all games with stats: {e}")
            return []
        finally:
            session.close()

    def log_game_session(self, user_id: int, game_name: str, hours: float, players: int = 1) -> None:
        """Log a new game session"""
        session = self.Session()
        try:
            # Normalize the game name (lowercase and strip extra spaces)
            normalized_name = ' '.join(game_name.lower().split())
            
            # Get the game using case-insensitive comparison
            game = session.query(Game).filter(func.lower(Game.name) == normalized_name).first()
            if not game:
                raise Exception("Game does not exist in the database, please set the rate")

            # Get user's total hours for this game (before this session)
            total_game_hours = session.query(func.sum(GamingSession.hours))\
                .filter(GamingSession.user_id == user_id, GamingSession.game_id == game.id)\
                .scalar() or 0.0

            # Calculate credits earned with half-life system based on total accumulated hours
            base_credits = self.calculate_credits_with_half_life_for_session(
                hours, 
                total_game_hours, 
                game.credits_per_hour, 
                game.half_life_hours
            )

            # Handle players parameter - convert string "5+" to integer 5
            if isinstance(players, str) and players == "5+":
                players = 5
            else:
                try:
                    players = int(players)
                except (ValueError, TypeError):
                    players = 1

            # Apply players bonus: +10% per extra player, up to 5 players (max 40% bonus)
            players = max(1, min(players, 5))
            credits_earned = base_credits * (1 + 0.1 * (players - 1))

            # Create timestamp in CST
            utc_now = datetime.now(pytz.UTC)
            cst_time = utc_now.astimezone(self.cst)

            # Create the gaming session
            gaming_session = GamingSession(
                user_id=user_id,
                game_id=game.id,
                hours=hours,
                credits_earned=credits_earned,
                timestamp=cst_time,
                players=players
            )
            session.add(gaming_session)
            session.commit()

        except Exception as e:
            session.rollback()
            raise Exception(str(e))
        finally:
            session.close()

    def search_games(self, query: str, limit: int = 10) -> List[Game]:
        """Search for games by name"""
        session = self.Session()
        try:
            # Search for games that match the query (case-insensitive)
            games = session.query(Game)\
                .filter(func.lower(Game.name).like(f'%{query.lower()}%'))\
                .order_by(Game.name)\
                .limit(limit)\
                .all()
            
            return games
        except Exception as e:
            print(f"Error searching games: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            return []
        finally:
            session.close()

    async def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get user statistics"""
        session = self.Session()
        try:
            # Get total credits and games played
            total_credits = session.query(func.sum(GamingSession.credits_earned))\
                .filter(GamingSession.user_id == user_id).scalar() or 0
            
            games_played = session.query(func.count(distinct(GamingSession.game_id)))\
                .filter(GamingSession.user_id == user_id).scalar() or 0

            # Get first and last played timestamps
            first_played = session.query(func.min(GamingSession.timestamp))\
                .filter(GamingSession.user_id == user_id).scalar()
            last_played = session.query(func.max(GamingSession.timestamp))\
                .filter(GamingSession.user_id == user_id).scalar()

            # Convert timestamps to CST if they exist
            if first_played and first_played.tzinfo is None:
                first_played = first_played.replace(tzinfo=pytz.UTC).astimezone(self.cst)
            if last_played and last_played.tzinfo is None:
                last_played = last_played.replace(tzinfo=pytz.UTC).astimezone(self.cst)

            # Get most played game
            most_played = session.query(
                Game.name,
                func.sum(GamingSession.hours).label('total_hours')
            ).join(Game, GamingSession.game_id == Game.id)\
             .filter(GamingSession.user_id == user_id)\
             .group_by(Game.name)\
             .order_by(text('total_hours DESC'))\
             .first()

            return {
                'total_credits': float(total_credits),
                'games_played': games_played,
                'first_played': first_played,
                'last_played': last_played,
                'most_played_game': most_played[0] if most_played else None,
                'most_played_hours': float(most_played[1]) if most_played else 0
            }

        except Exception as e:
            print(f"Error getting user stats: {str(e)}")
            return None
        finally:
            session.close()

    def update_game_capitalization(self):
        """Update the capitalization of all existing games."""
        session = self.Session()
        try:
            games = session.query(Game).all()
            for game in games:
                # First, capitalize the first letter of the entire string
                game_name = game.name.strip()
                if game_name:
                    game_name = game_name[0].upper() + game_name[1:]
                
                # Then capitalize each word, preserving Roman numerals
                words = game_name.split()
                formatted_words = []
                for word in words:
                    # Check if the word is a Roman numeral (case-insensitive)
                    if word.upper() in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV']:
                        formatted_words.append(word.upper())
                    else:
                        formatted_words.append(word.capitalize())
                
                formatted_name = ' '.join(formatted_words)
                
                if formatted_name != game.name:
                    print(f"Updating game name from '{game.name}' to '{formatted_name}'")
                    game.name = formatted_name
                    session.add(game)
            
            session.commit()
            print("Finished updating game capitalization")
        except Exception as e:
            session.rollback()
            print(f"Error updating game capitalization: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
        finally:
            session.close()

    def get_user_daily_credits(self, user_id: str) -> List[Dict]:
        """Get total credits earned per day for a user."""
        session = self.Session()
        try:
            results = session.execute(text("""
                SELECT DATE(gs.timestamp) as date, SUM(gs.credits_earned) as credits
                FROM gaming_sessions gs
                WHERE gs.user_id = :user_id
                GROUP BY DATE(gs.timestamp)
                ORDER BY date ASC
            """), {"user_id": user_id}).fetchall()
            return [{"date": str(row.date), "credits": float(row.credits)} for row in results]
        finally:
            session.close()

    async def set_game_half_life(self, game_name: str, half_life_hours: float, user_id: int) -> bool:
        """Set half-life hours for a game"""
        session = self.Session()
        try:
            # Format the game name
            formatted_name = ' '.join(word.capitalize() for word in game_name.split())
            
            # Get existing game
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(formatted_name)).first()
            
            if game:
                # Update existing game
                game.half_life_hours = half_life_hours if half_life_hours > 0 else None
                game.added_by = user_id
                
                # Recalculate all existing gaming sessions for this game with new half-life
                gaming_sessions = session.query(GamingSession).filter(GamingSession.game_id == game.id).all()
                for gaming_session in gaming_sessions:
                    # Recalculate credits based on hours and new half-life
                    new_credits = self.calculate_credits_with_half_life(
                        gaming_session.hours, 
                        game.credits_per_hour, 
                        game.half_life_hours
                    )
                    gaming_session.credits_earned = new_credits
            else:
                # Game doesn't exist, create it with default CPH
                game = Game(
                    name=formatted_name, 
                    credits_per_hour=1.0,  # Default CPH
                    half_life_hours=half_life_hours if half_life_hours > 0 else None,
                    added_by=user_id
                )
                session.add(game)
            
            session.commit()
            
            # Recalculate user totals since credits may have changed
            self.recalculate_all_user_credits()
            
            return True

        except Exception as e:
            session.rollback()
            print(f"Error setting game half-life: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            return False
        finally:
            session.close()

    def set_game_box_art(self, game_name: str, box_art_url: str, user_id: int) -> bool:
        """Set box art URL for a game"""
        session = self.Session()
        try:
            # Format the game name
            formatted_name = ' '.join(word.capitalize() for word in game_name.split())
            
            # Get existing game
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(formatted_name)).first()
            
            if game:
                # Update existing game
                game.box_art_url = box_art_url if box_art_url else None
                game.added_by = user_id
                session.commit()
                return True
            else:
                # Game doesn't exist, create it with default values
                game = Game(
                    name=formatted_name, 
                    credits_per_hour=1.0,  # Default CPH
                    box_art_url=box_art_url if box_art_url else None,
                    added_by=user_id
                )
                session.add(game)
                session.commit()
                return True

        except Exception as e:
            session.rollback()
            print(f"Error setting game box art: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            return False
        finally:
            session.close()

    def get_recent_rate_changes(self, limit: int = 10) -> List[Dict]:
        """Get recent rate changes for games"""
        session = self.Session()
        try:
            # Get recent games that have been modified
            # Since we don't have a dedicated rate changes table, we'll get recent games
            # and their current settings as a proxy for recent changes
            games = session.query(Game)\
                .filter(Game.added_by.isnot(None))\
                .order_by(Game.id.desc())\
                .limit(limit)\
                .all()
            
            changes = []
            for game in games:
                # Get user info for the person who set the rate
                user_id = str(game.added_by) if game.added_by else None
                
                changes.append({
                    'game_name': game.name,
                    'current_cph': game.credits_per_hour,
                    'current_half_life': game.half_life_hours,
                    'box_art_url': game.box_art_url,
                    'user_id': user_id,
                    'user_name': f'User{user_id}' if user_id else 'Unknown',
                    'timestamp': datetime.now().isoformat()  # Since we don't track when rates were set
                })
            
            return changes

        except Exception as e:
            print(f"Error getting recent rate changes: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            return []
        finally:
            session.close()

def get_period_boundaries(dt: datetime, period_type: str):
    """Return (start, end) datetime for the period containing dt. period_type is 'weekly' or 'monthly'. All times in CST."""
    cst = pytz.timezone('America/Chicago')
    dt = dt.astimezone(cst)
    if period_type == 'weekly':
        days_since_monday = dt.weekday()
        start = (dt - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
    elif period_type == 'monthly':
        start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if dt.month == 12:
            end = dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            end = dt.replace(month=dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError('period_type must be weekly or monthly')
    return start, end