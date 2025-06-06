import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy import create_engine, func, DateTime as sqlalchemy_DateTime, and_, Integer, String, BigInteger, text
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, Game, UserStats, GamingSession, LeaderboardHistory, LeaderboardType, LeaderboardPeriod, Bonus # Removed User import
import pytz
import discord
from dotenv import load_dotenv
import aiohttp
import asyncio
from collections import defaultdict
from sqlalchemy.sql import select
import traceback

# Load environment variables
load_dotenv()

class GameStorage:
    def __init__(self):
        print("DEBUG: Initializing GameStorage")
        # Get database URL from environment variables
        database_url = os.getenv('DATABASE_URL')
        print(f"DEBUG: Using database URL: {database_url}")
        
        # Initialize timezone
        self.cst = pytz.timezone('America/Chicago')
        print("DEBUG: Initialized CST timezone")
        
        if not database_url:
            raise ValueError("No database URL found. Set DATABASE_URL to your PostgreSQL connection string")
        
        try:
            print("DEBUG: Using PostgreSQL database")
            self.engine = create_engine(database_url)
            print("DEBUG: Database engine created successfully")
            
            # Test the connection
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1")).scalar()
                print(f"DEBUG: Database connection test result: {result}")
                if result != 1:
                    raise Exception("Database connection test failed")
                print("DEBUG: Database connection test successful")
                
                # Print database version
                version = connection.execute(text("SELECT version()")).scalar()
                print(f"DEBUG: Database version: {version}")
        except Exception as e:
            print(f"ERROR: Failed to initialize database connection: {str(e)}")
            print("Full traceback:")
            import traceback
            traceback.print_exc()
            raise

    def Session(self):
        return sessionmaker(bind=self.engine)()

    def _initialize_db(self):
        """Initialize the database connection"""
        try:
            print(f"Initializing database with URL: {self.database_url}")

            # Create PostgreSQL engine
            print("Using PostgreSQL database")
            print(f"PostgreSQL URL: {self.database_url}")
            self.engine = create_engine(self.database_url)
            print("PostgreSQL engine created")

            # Initialize session maker
            print("Initializing session maker...")
            self.Session = scoped_session(
                sessionmaker(
                    bind=self.engine,
                    expire_on_commit=False
                )
            )
            print("Session maker initialized")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            print(f"Current working directory: {os.getcwd()}")
            raise

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
                        print(f"Sent period end announcement to {announcement_channel.name} in {guild.name}")
                    except discord.errors.Forbidden:
                        print(f"Cannot send messages in {announcement_channel.name} ({guild.name})")
                    except Exception as e:
                        print(f"Error sending announcement in {guild.name}: {str(e)}")

        except Exception as e:
            print(f"Error creating leaderboard announcement: {str(e)}")
        finally:
            session.close()

    def get_or_create_current_period(self, leaderboard_type: LeaderboardType, bot=None) -> LeaderboardPeriod:
        """Get or create the current leaderboard period."""
        print(f"\n=== DEBUG: Getting/creating current period for {leaderboard_type} ===")
        session = self.Session()
        try:
            # Use naive current time and localize to CST
            naive_now = datetime.now()
            current_time = self.cst.localize(naive_now)
            print(f"DEBUG: Current time in CST: {current_time}")

            # Calculate period start time based on leaderboard type
            if leaderboard_type == LeaderboardType.WEEKLY:
                # Start of current week (Monday)
                period_start = current_time - timedelta(days=current_time.weekday())
                period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(days=7)
            else:  # MONTHLY
                # Start of current month
                period_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                # Start of next month
                if current_time.month == 12:
                    period_end = current_time.replace(year=current_time.year + 1, month=1, day=1)
                else:
                    period_end = current_time.replace(month=current_time.month + 1, day=1)
                period_end = period_end.replace(hour=0, minute=0, second=0, microsecond=0)

            print(f"DEBUG: Period start: {period_start}")
            print(f"DEBUG: Period end: {period_end}")

            # Check if we already have a period for this timeframe
            existing_period = session.query(LeaderboardPeriod).filter(
                and_(
                    LeaderboardPeriod.leaderboard_type == leaderboard_type,
                    LeaderboardPeriod.start_time == period_start,
                    LeaderboardPeriod.end_time == period_end
                )
            ).first()

            if existing_period:
                print(f"DEBUG: Found existing period: {existing_period}")
                return existing_period

            # Create new period
            print("DEBUG: Creating new period")
            new_period = LeaderboardPeriod(
                leaderboard_type=leaderboard_type,
                start_time=period_start,
                end_time=period_end,
                is_active=True
            )
            session.add(new_period)
            session.commit()
            print(f"DEBUG: Created new period: {new_period}")

            # If we have a bot and this is a new period, announce it
            if bot:
                asyncio.create_task(self.announce_period_end(bot, leaderboard_type, new_period))

            return new_period

        except Exception as e:
            print(f"ERROR: Failed to get/create period: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            session.rollback()
            raise
        finally:
            session.close()

    def get_leaderboard_by_timeframe(self, timeframe: LeaderboardType) -> List[Tuple[int, int, int, str, int]]:
        """Get leaderboard data for a specific timeframe."""
        print(f"\n=== DEBUG: Getting leaderboard for timeframe {timeframe} ===")
        db_session = self.Session()
        try:
            # Get the current period
            print("DEBUG: Getting current period...")
            current_period = self.get_or_create_current_period(timeframe)
            print(f"DEBUG: Current period: {current_period}")
            print(f"DEBUG: Period start: {current_period.start_time}")
            print(f"DEBUG: Period end: {current_period.end_time}")

            # Use a single query to get all the data we need
            print("DEBUG: Executing optimized leaderboard query...")
            results = db_session.query(
                GamingSession.user_id,
                func.sum(GamingSession.credits_earned).label('total_credits'),
                func.count(GamingSession.game_id.distinct()).label('games_played'),
                func.max(Game.name).label('most_played_game'),
                func.sum(GamingSession.hours).label('most_played_hours')
            ).join(
                Game, GamingSession.game_id == Game.id
            ).filter(
                and_(
                    GamingSession.timestamp >= current_period.start_time,
                    GamingSession.timestamp < current_period.end_time
                )
            ).group_by(
                GamingSession.user_id
            ).order_by(
                func.sum(GamingSession.credits_earned).desc()
            ).all()

            print(f"DEBUG: Found {len(results)} users in leaderboard")
            
            # Format the results
            leaderboard = []
            for user_id, credits, games_played, most_played_game, most_played_hours in results:
                leaderboard.append((user_id, credits, games_played, most_played_game, most_played_hours))
                print(f"DEBUG: Added user {user_id} to leaderboard with {credits} credits")

            print(f"DEBUG: Final leaderboard: {leaderboard}")
            return leaderboard

        except Exception as e:
            print(f"ERROR: Failed to get leaderboard: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            raise
        finally:
            db_session.close()

    async def record_leaderboard_placements(self, leaderboard_type: LeaderboardType, placements: List[Tuple[int, float, int, str, float]], period: LeaderboardPeriod) -> None:
        """Record placements for the given leaderboard period"""
        session = self.Session()
        try:
            # Use naive current time and localize to CST
            naive_now = datetime.now()
            current_time = self.cst.localize(naive_now)

            # Debug logging
            print(f"\nRecording placements for {leaderboard_type.value}:")
            print(f"Period: {period.start_time} to {period.end_time} CST")
            print(f"Number of placements: {len(placements)}")

            # Check if we already have records for this period
            existing_records = session.query(LeaderboardHistory)\
                .filter(LeaderboardHistory.period_id == period.id)\
                .all()

            if existing_records:
                print(f"Found {len(existing_records)} existing records for this period - updating")
                # Delete existing records for this period
                for record in existing_records:
                    session.delete(record)
                session.commit()

            # Record each placement
            for position, (user_id, credits, games, most_played, most_played_hours) in enumerate(placements, 1):
                history = LeaderboardHistory(
                    user_id=user_id,
                    period_id=period.id,
                    leaderboard_type=leaderboard_type,
                    placement=position,
                    credits=credits,
                    games_played=games,
                    most_played_game=most_played,
                    most_played_hours=most_played_hours,
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

    def get_user_gaming_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's recent gaming history"""
        session = self.Session()
        try:
            # Get recent sessions with game info in a single query
            results = session.execute(text("""
                SELECT 
                    g.name as game,
                    gs.hours,
                    gs.credits_earned,
                    g.credits_per_hour as rate,
                    gs.timestamp
                FROM gaming_sessions gs
                JOIN games g ON g.id = gs.game_id
                WHERE gs.user_id = :user_id
                ORDER BY gs.timestamp DESC
                LIMIT :limit
            """), {
                "user_id": user_id,
                "limit": limit
            }).fetchall()

            return [{
                "game": row.game,
                "hours": float(row.hours),
                "credits_earned": float(row.credits_earned),
                "rate": float(row.rate),
                "timestamp": row.timestamp
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

    async def get_or_create_game(self, game_name: str, user_id: int, credits_per_hour: float = 1.0) -> Tuple[Game, bool]:
        """Get a game by name or create it if it doesn't exist, and fetch/update RAWG data."""
        session = self.Session()
        try:
            # Case-insensitive search for existing game
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(game_name)).first()
            created = False

            if not game:
                # Capitalize the first letter for consistency
                formatted_name = game_name.strip().capitalize()
                
                # Create the Backloggd URL by replacing spaces with hyphens and converting to lowercase
                # Also handle special characters and apostrophes
                url_name = formatted_name.lower()
                # Replace apostrophes and quotes with empty string
                url_name = url_name.replace("'", "").replace('"', "")
                # Replace spaces and special characters with hyphens
                url_name = ''.join(c if c.isalnum() else '-' for c in url_name)
                # Replace multiple hyphens with a single hyphen
                url_name = '-'.join(filter(None, url_name.split('-')))
                
                backloggd_url = f"https://www.backloggd.com/games/{url_name}/"
                
                game = Game(
                    name=formatted_name, 
                    credits_per_hour=credits_per_hour, 
                    added_by=user_id,
                    backloggd_url=backloggd_url
                )
                session.add(game)
                session.commit() # Commit to get the game ID for relationships
                created = True
                print(f"Created new game: {game.name}")

            # Fetch and update RAWG data if missing
            if game and (game.rawg_id is None or game.box_art_url is None):
                print(f"Fetching RAWG data for {game.name}...")
                rawg_details = await self.fetch_game_details_from_rawg(game.name)
                if rawg_details:
                    game.rawg_id = rawg_details['rawg_id']
                    game.box_art_url = rawg_details['box_art_url']
                    # Optionally update game name with RAWG display name if preferred
                    # game.name = rawg_details['display_name']
                session.add(game)
                session.commit()
                print(f"Updated RAWG data for {game.name}")
            else:
                print(f"Failed to fetch RAWG data for {game.name}. Using defaults/placeholders.")

            return game, created
        except Exception as e:
            session.rollback()
            print(f"Error in get_or_create_game for {game_name}: {e}")
            raise e # Re-raise the exception
        finally:
            session.close()

    async def set_game_credits_per_hour(self, game_name: str, credits: float, user_id: int) -> bool:
        """Set credits per hour for a game and update all existing sessions"""
        if credits < 0.1:  # Only keep minimum limit
            return False

        print(f"Starting set_game_credits_per_hour for {game_name}")
        
        # Try up to 3 times with a new session each time
        for attempt in range(3):
            print(f"Attempt {attempt + 1} of 3")
            session = self.Session()
            try:
                # Case-insensitive search for existing game
                print(f"Searching for existing game: {game_name}")
                game = session.query(Game).filter(func.lower(Game.name) == func.lower(game_name)).first()

                if game:
                    print(f"Found existing game: {game.name}")
                    # Update existing game
                    game.credits_per_hour = credits
                    game.added_by = user_id
                    print("Committing update...")
                    session.commit()
                    print("Update committed successfully")
                    return True
                else:
                    print(f"Game not found, creating new game: {game_name}")
                    # Create new game
                    formatted_name = game_name.strip()
                    
                    # Create the Backloggd URL
                    url_name = formatted_name.lower()
                    url_name = url_name.replace("'", "").replace('"', "")
                    url_name = ''.join(c if c.isalnum() else '-' for c in url_name)
                    url_name = '-'.join(filter(None, url_name.split('-')))
                    
                    backloggd_url = f"https://www.backloggd.com/games/{url_name}/"
                    
                    # Fetch RAWG data
                    print("Fetching RAWG data...")
                    rawg_data = await self.fetch_game_details_from_rawg(formatted_name)
                    print(f"DEBUG: RAWG data received: {rawg_data}")
                    
                    rawg_id = rawg_data.get('id') if rawg_data else None
                    box_art_url = rawg_data.get('box_art_url') if rawg_data else None
                    print(f"DEBUG: Extracted rawg_id: {rawg_id}")
                    print(f"DEBUG: Extracted box_art_url: {box_art_url}")
                    
                    print("Creating new game object...")
                    game = Game(
                        name=formatted_name, 
                        credits_per_hour=credits, 
                        added_by=user_id,
                        backloggd_url=backloggd_url,
                        rawg_id=rawg_id,
                        box_art_url=box_art_url
                    )
                    print(f"DEBUG: Created game object with box_art_url: {game.box_art_url}")
                    print("Adding game to session...")
                    session.add(game)
                    print("Committing new game...")
                    
                    # Set a timeout for the commit
                    from sqlalchemy.exc import SQLAlchemyError
                    try:
                        session.commit()
                        print("New game committed successfully")
                        # Verify the data was saved
                        saved_game = session.query(Game).filter(Game.name == formatted_name).first()
                        print(f"DEBUG: Saved game box_art_url: {saved_game.box_art_url}")
                        return True
                    except SQLAlchemyError as e:
                        print(f"Database error during commit: {str(e)}")
                        session.rollback()
                        if attempt < 2:  # If not the last attempt
                            print("Retrying with new session...")
                            continue
                        raise  # Re-raise on last attempt

            except Exception as e:
                print(f"Error in set_game_credits_per_hour: {str(e)}")
                print(f"Error type: {type(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                session.rollback()
                if attempt < 2:  # If not the last attempt
                    print("Retrying with new session...")
                    continue
                return False
            finally:
                print("Closing session...")
                session.close()
                print("Session closed")
        
        return False  # If we get here, all attempts failed

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
                print("Detected direct changes to game rates, recalculating credits...")
                self.recalculate_all_credits()
                # Refresh the provided session to see the updates
                session.expire_all()
                session.commit()
                return True

            return False
        except Exception as e:
            print(f"Error checking credit updates: {str(e)}")
            return False

    def recalculate_all_credits(self) -> None:
        """Recalculate all credits based on current game rates"""
        session = self.Session()
        try:
            print("Starting credit recalculation...")

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
                    # Calculate new credits based on current rate
                    new_credits = gaming_session.hours * game.credits_per_hour

                    # Update credits regardless of whether they've changed
                    gaming_session.credits_earned = new_credits
                    updated_sessions += 1

            print(f"Recalculation complete: Updated {updated_sessions} of {total_sessions} sessions")
            session.commit()

            # Now recalculate all user totals based on their sessions
            self.recalculate_all_user_credits()

        except Exception as e:
            print(f"Error recalculating credits: {str(e)}")
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
            print("Recalculating all user credits from gaming sessions...")

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
                session.commit()

                # Update or create user stats
                user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
                if not user_stats:
                    user_stats = UserStats(user_id=user_id, total_credits=total_credits)
                    session.add(user_stats)
                else:
                    user_stats.total_credits = total_credits

                print(f"Updated User {user_id}: {total_credits:,.1f} credits")

            session.commit()
            print("Credit recalculation complete!")

        except Exception as e:
            print(f"Error recalculating credits: {str(e)}")
            session.rollback()
        finally:
            session.close()

    async def add_gaming_hours(self, user_id: int, hours: float, game_name: str) -> float:
        """Add gaming hours for a user and return credits earned"""
        session = self.Session()
        try:
            # Get or create the game
            game = session.query(Game).filter(func.lower(Game.name) == func.lower(game_name)).first()
            if not game:
                # Create new game with default credits per hour
                game = Game(
                    name=game_name,
                    credits_per_hour=1.0,
                    added_by=user_id
                )
                session.add(game)
                session.commit()

            # Calculate credits earned
            credits_earned = hours * game.credits_per_hour

            # Get the next available ID for gaming_sessions
            next_id = session.query(func.max(GamingSession.id)).scalar() or 0
            next_id += 1

            # Create gaming session
            gaming_session = GamingSession(
                id=next_id,
                user_id=user_id,
                game_id=game.id,
                hours=hours,
                credits_earned=credits_earned,
                timestamp=datetime.now(self.cst)
            )
            session.add(gaming_session)

            # Get or create user stats
            user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
            if not user_stats:
                user_stats = UserStats(
                    user_id=user_id,
                    total_credits=0.0
                )
                session.add(user_stats)

            # Update user's total credits
            user_stats.total_credits += credits_earned

            session.commit()

            # Update leaderboard history for active periods
            active_periods = session.query(LeaderboardPeriod)\
                .filter(LeaderboardPeriod.is_active == True)\
                .all()

            for period in active_periods:
                # Get current leaderboard data for this period
                leaderboard_data = await self.get_leaderboard_by_timeframe(period.leaderboard_type)
                if leaderboard_data:
                    # Record the updated placements
                    await self.record_leaderboard_placements(period.leaderboard_type, leaderboard_data, period)

            return credits_earned

        except Exception as e:
            print(f"Error adding gaming hours: {str(e)}")
            session.rollback()
            raise
        finally:
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
                        COALESCE(SUM(credits_earned), 0) as total_credits,
                        COUNT(DISTINCT game_id) as games_played,
                        COUNT(*) as total_sessions,
                        MIN(timestamp) as first_played,
                        MAX(timestamp) as last_played
                    FROM gaming_sessions
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
                        RANK() OVER (ORDER BY COALESCE(SUM(credits_earned), 0) DESC) as rank
                    FROM gaming_sessions
                    GROUP BY user_id
                )
                SELECT 
                    us.*,
                    mp.name as most_played_game,
                    mp.total_hours as most_played_hours,
                    ur.rank
                FROM user_stats us
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
                "added_by": game.added_by,
                "backloggd_url": game.backloggd_url,
                "box_art_url": game.box_art_url,
                "rawg_id": game.rawg_id
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
                    COUNT(*) as sessions
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
                "sessions": row.sessions
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

    async def get_total_game_hours_by_timeframe(self, timeframe: str) -> List[Tuple[str, float, str]]:
        """Get the total hours played for each game within a given timeframe."""
        print(f"DEBUG: Starting get_total_game_hours_by_timeframe for timeframe: {timeframe}")
        session = self.Session()
        try:
            print(f"DEBUG: Created database session")
            query = session.query(
                Game.name,
                func.sum(GamingSession.hours).label('total_hours'),
                Game.box_art_url
            ).join(Game, GamingSession.game_id == Game.id)

            print(f"DEBUG: Created base query")

            # Get current time in CST
            current_time = datetime.now(self.cst)
            print(f"DEBUG: Current time in CST: {current_time}")
            start_time = None

            if timeframe == 'weekly':
                # Start from last Monday 00:00 CST
                days_since_monday = current_time.weekday()
                start_time = (current_time - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                print(f"DEBUG: Weekly start time: {start_time}")
            elif timeframe == 'monthly':
                # Start from 1st of current month CST
                start_time = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                print(f"DEBUG: Monthly start time: {start_time}")
            elif timeframe == 'alltime':
                print("DEBUG: No time filter for alltime timeframe")
            else:
                print(f"DEBUG: Invalid timeframe specified: {timeframe}")
                return []

            if start_time:
                query = query.filter(GamingSession.timestamp >= start_time)
                print(f"DEBUG: Added time filter: {start_time}")

            # Group by both game name and box_art_url
            query = query.group_by(Game.name, Game.box_art_url)
            query = query.order_by(text('total_hours DESC'))

            print("DEBUG: About to execute query...")
            print(f"DEBUG: Query SQL: {query.statement.compile(compile_kwargs={'literal_binds': True})}")
            
            results = query.all()
            print(f"DEBUG: Query executed successfully. Number of results: {len(results)}")
            print(f"DEBUG: Raw query results: {results}")
            
            # Format results as list of tuples (game_name, total_hours, box_art_url)
            formatted_results = [(r.name, float(r.total_hours), r.box_art_url) for r in results]
            print(f"DEBUG: Formatted results: {formatted_results}")
            
            return formatted_results

        except Exception as e:
            print(f"ERROR: Error getting total game hours for timeframe {timeframe}: {str(e)}")
            print("Full traceback:")
            import traceback
            traceback.print_exc()
            return []
        finally:
            print("DEBUG: Closing database session")
            session.close()

    async def fetch_game_details_from_rawg(self, game_name: str) -> Optional[Dict]:
        """Fetch game details from RAWG API, including box art and description."""
        rawg_api_key = os.getenv('RAWG_API_KEY') # Get RAWG API key
        rawg_api_url = os.getenv('RAWG_API_URL', 'https://api.rawg.io/api') # Get RAWG API URL

        print(f"DEBUG: Fetching RAWG data for game: {game_name}")
        print(f"DEBUG: RAWG API Key present: {bool(rawg_api_key)}")
        print(f"DEBUG: RAWG API URL: {rawg_api_url}")

        if not rawg_api_key:
            print("RAWG_API_KEY not set. Cannot fetch game details from RAWG.")
            return None

        try:
            # Step 1: Search for the game by name
            search_url = f'{rawg_api_url}/games'
            search_params = {'key': rawg_api_key, 'search': game_name, 'page_size': 1}
            print(f"DEBUG: Searching RAWG with URL: {search_url}")
            print(f"DEBUG: Search params: {search_params}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=search_params) as response:
                    if response.status != 200:
                        print(f"RAWG search API error for '{game_name}': {response.status}")
                        return None
                    search_data = await response.json()
                    print(f"DEBUG: RAWG search response: {search_data}")

            if not search_data or not search_data['results']:
                print(f"No RAWG search results found for '{game_name}'.")
                return None

            # Get the ID of the first result
            game_id = search_data['results'][0]['id']
            rawg_display_name = search_data['results'][0].get('name', game_name)
            print(f"DEBUG: Found game ID: {game_id}")
            print(f"DEBUG: RAWG display name: {rawg_display_name}")

            # Step 2: Get full game details by ID
            details_url = f'{rawg_api_url}/games/{game_id}'
            details_params = {'key': rawg_api_key}
            print(f"DEBUG: Fetching game details from: {details_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(details_url, params=details_params) as response:
                    if response.status != 200:
                        print(f"RAWG details API error for ID {game_id}: {response.status}")
                        return None
                    details_data = await response.json()
                    print(f"DEBUG: RAWG details response: {details_data}")

            # Get box art URL and description
            box_art_url = details_data.get('background_image')
            description = details_data.get('description_raw', 'No description available.')
            print(f"DEBUG: Box art URL: {box_art_url}")
            print(f"DEBUG: Description length: {len(description)}")

            return {
                'id': game_id,  # Changed from 'rawg_id' to 'id' to match the database column
                'display_name': rawg_display_name,
                'box_art_url': box_art_url,  # Changed from 'background_image' to 'box_art_url'
                'description': description
            }

        except Exception as e:
            print(f"Error fetching game details from RAWG for '{game_name}': {e}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            return None

    async def get_recent_gaming_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the most recent gaming sessions with game details."""
        session = self.Session()
        try:
            print(f"DEBUG: Getting recent gaming sessions, limit: {limit}")
            # Fetch recent gaming sessions with game details
            sessions_query = session.query(
                GamingSession.id,
                GamingSession.user_id,
                GamingSession.game_id,
                GamingSession.hours,
                GamingSession.timestamp,
                Game.name.label('game_name'),
                Game.box_art_url
            ).join(Game, GamingSession.game_id == Game.id, isouter=True)\
             .order_by(GamingSession.timestamp.desc())\
             .limit(limit)

            print("DEBUG: Executing query...")
            rows = sessions_query.all()
            print(f"DEBUG: get_recent_gaming_sessions - Fetched rows: {rows}") # Debug print

            # If no real sessions, return empty list (Discord info will be fetched in app.py)
            if not rows:
                 print("DEBUG: get_recent_gaming_sessions - No rows found.") # Debug print
                 return []

            # Format the results (only include data directly from DB for now)
            sessions_data = []
            for row in rows:
                sessions_data.append({
                    'id': row.id,
                    'user_id': str(row.user_id),  # Convert user_id to string to preserve precision
                    'game_id': row.game_id,
                    'hours': row.hours,
                    'timestamp': row.timestamp,
                    'game_name': row.game_name or f'Game{row.game_id}', # Fallback
                    'box_art_url': row.box_art_url # Can be None
                })

            print(f"DEBUG: get_recent_gaming_sessions - Returning data: {sessions_data}") # Debug print
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
            print(f"DEBUG: Getting recent bonuses, limit: {limit}")
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

            print("DEBUG: Executing query...")
            rows = bonuses_query.all()
            print(f"DEBUG: get_recent_bonuses - Fetched rows: {rows}") # Debug print

            # Format the results as a list of dictionaries
            recent_bonuses = []
            for row in rows:
                # Convert row to dictionary
                bonus_data = {
                    'id': row.id,
                    'user_id': row.user_id,
                    'credits': row.credits,
                    'reason': row.reason,
                    'granted_by': row.granted_by,
                    'timestamp': row.timestamp
                }
                recent_bonuses.append(bonus_data)

            # If no real bonuses, return empty list (frontend handles display)
            if not recent_bonuses:
                print("DEBUG: get_recent_bonuses - No bonuses found.") # Debug print
                return []

            print(f"DEBUG: get_recent_bonuses - Returning {len(recent_bonuses)} bonuses") # Debug print
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
            # Get naive current time and localize to CST
            naive_now = datetime.now()
            now = self.cst.localize(naive_now)

            start_time = None
            end_time = now # End time is always now for current period calculations

            if timeframe == 'weekly':
                # Start from last Monday 00:00 CST
                days_since_monday = naive_now.weekday()
                naive_start = (naive_now - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                start_time = self.cst.localize(naive_start)
            elif timeframe == 'monthly':
                # Start from 1st of current month CST
                naive_start = naive_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                start_time = self.cst.localize(naive_start)
            elif timeframe == 'alltime':
                # No start time limit for all-time
                start_time = None # Set start_time to None for all-time
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
                 # Ensure both timestamp and start_time are timezone-aware or naive for comparison
                 # Assuming GamingSession.timestamp is stored as TZDateTime and thus timezone-aware
                query = query.filter(GamingSession.timestamp >= start_time)

            query = query.group_by(Game.id, Game.name, Game.box_art_url)\
                         .order_by(func.sum(GamingSession.hours).desc())\
                         .limit(limit)

            results = query.all()

            # Format the results as a list of dictionaries
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'game_name': result.name,
                    'total_hours': result.total_hours,
                    'box_art_url': result.box_art_url
                })

            print(f"DEBUG: get_user_most_played_game_by_timeframe for user {user_id}, timeframe {timeframe}: {formatted_results}") # Debug print
            return formatted_results # Return a list of dictionaries

        except Exception as e:
            print(f"Error in get_user_most_played_game_by_timeframe for user {user_id}, timeframe {timeframe}: {e}")
            return []

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

    def get_recent_activity_for_game(self, game_name: str, limit: int = 10) -> List[Dict[str, Any]]:
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
                    'user_id': row.user_id,
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

    def calculate_credits(self, duration_minutes: int) -> float:
        """Calculate credits earned for a given duration in minutes."""
        # Base rate is 1 credit per hour
        base_rate = 1.0
        hours = duration_minutes / 60.0
        return base_rate * hours

    def get_alltime_leaderboard(self) -> List[Tuple[int, int, int, str, int]]:
        """Get all-time leaderboard data."""
        print("\n=== DEBUG: Getting all-time leaderboard ===")
        db_session = self.Session()
        try:
            # Use a single query to get all the data we need
            print("DEBUG: Executing optimized all-time leaderboard query...")
            results = db_session.query(
                GamingSession.user_id,
                func.sum(GamingSession.credits_earned).label('total_credits'),
                func.count(GamingSession.game_id.distinct()).label('games_played'),
                func.max(Game.name).label('most_played_game'),
                func.sum(GamingSession.hours).label('most_played_hours')
            ).join(
                Game, GamingSession.game_id == Game.id
            ).group_by(
                GamingSession.user_id
            ).order_by(
                func.sum(GamingSession.credits_earned).desc()
            ).all()

            print(f"DEBUG: Found {len(results)} users in all-time leaderboard")
            
            # Format the results
            leaderboard = []
            for user_id, credits, games_played, most_played_game, most_played_hours in results:
                leaderboard.append((user_id, credits, games_played, most_played_game, most_played_hours))
                print(f"DEBUG: Added user {user_id} to leaderboard with {credits} credits")

            print(f"DEBUG: Final leaderboard: {leaderboard}")
            return leaderboard

        except Exception as e:
            print(f"ERROR: Failed to get all-time leaderboard: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            raise
        finally:
            db_session.close()