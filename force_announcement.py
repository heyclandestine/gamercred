import asyncio
import discord
from datetime import datetime, timedelta
import pytz
from storage import GameStorage
from models import LeaderboardType, LeaderboardPeriod, LeaderboardHistory
from sqlalchemy import and_, func, create_engine, text
from dotenv import load_dotenv
import os
import argparse
from models import GamingSession, Game

# Load environment variables
load_dotenv()

# Get token from environment
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

if not TOKEN:
    raise ValueError("No Discord token found. Set DISCORD_TOKEN environment variable")
if not DATABASE_URL:
    raise ValueError("No database URL found. Set DATABASE_URL environment variable")

print(f"Using database URL: {DATABASE_URL}")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Force leaderboard announcements')
parser.add_argument('--force', action='store_true', help='Force announcement regardless of period end date')
parser.add_argument('--weekly', action='store_true', help='Process weekly leaderboard only')
parser.add_argument('--monthly', action='store_true', help='Process monthly leaderboard only')
args = parser.parse_args()

# Test database connection first
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Database connection successful!")
except Exception as e:
    print(f"Error connecting to database: {str(e)}")
    raise

# Create Discord client with all necessary intents
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord"""
    print(f"Bot is ready! Connected as {bot.user.name}")
    print(f"Connected to {len(bot.guilds)} guilds:")
    for guild in bot.guilds:
        print(f"- {guild.name} (ID: {guild.id})")
        print(f"  Channels: {len(guild.text_channels)}")
        for channel in guild.text_channels:
            print(f"  - {channel.name} (ID: {channel.id})")
    
    # Initialize storage
    print("Initializing storage...")
    storage = GameStorage()
    
    # Process leaderboards based on command line arguments
    if args.weekly or (not args.weekly and not args.monthly):
        print("\nProcessing weekly leaderboard...")
        try:
            await asyncio.wait_for(
                process_leaderboard_period(bot, storage, LeaderboardType.WEEKLY),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            print("Timed out processing weekly leaderboard")
        except Exception as e:
            print(f"Error processing weekly leaderboard: {str(e)}")
    
    if args.monthly or (not args.weekly and not args.monthly):
        print("\nProcessing monthly leaderboard...")
        try:
            await asyncio.wait_for(
                process_leaderboard_period(bot, storage, LeaderboardType.MONTHLY),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            print("Timed out processing monthly leaderboard")
        except Exception as e:
            print(f"Error processing monthly leaderboard: {str(e)}")
    
    print("\nLeaderboard processing complete!")
    print("Closing bot connection...")
    await bot.close()
    print("Bot connection closed")

async def announce_leaderboard_results(bot, storage, period):
    """Announce the results for a specific leaderboard period"""
    print(f"Announcing results for period: {period.start_time} to {period.end_time}")
    
    session = storage.Session()
    try:
        # Get placements for this period
        placements = session.query(LeaderboardHistory).filter(
            LeaderboardHistory.period_id == period.id
        ).order_by(LeaderboardHistory.placement).all()
        
        if not placements:
            print("No placements found for this period")
            return
        
        print(f"Found {len(placements)} placements to announce")
        
        # Create the announcement embed
        period_type = "Weekly" if period.leaderboard_type == LeaderboardType.WEEKLY else "Monthly"
        embed = discord.Embed(
            title=f"🏆 {period_type} Leaderboard Results",
            description=f"Period: {period.start_time.strftime('%Y-%m-%d')} to {period.end_time.strftime('%Y-%m-%d')}",
            color=0xffd700  # Gold color
        )
        
        # Add placements to the embed
        for placement in placements:
            # Get member object
            member = None
            for guild in bot.guilds:
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
        
        print("Created announcement embed")
        
        # Send the announcement to all guilds
        for guild in bot.guilds:
            print(f"\nProcessing guild: {guild.name}")
            
            # Find the general channel
            general_channel = None
            for channel in guild.text_channels:
                if channel.name.lower() == "general":
                    general_channel = channel
                    print(f"Found general channel: {channel.name}")
                    break
            
            # If no general channel found, try to find any channel with send permissions
            if not general_channel:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        general_channel = channel
                        print(f"No general channel found, using: {channel.name}")
                        break
            
            if general_channel:
                try:
                    print(f"Attempting to send announcement to {general_channel.name} in {guild.name}")
                    await general_channel.send(embed=embed)
                    print(f"Successfully sent period end announcement to {general_channel.name} in {guild.name}")
                except discord.errors.Forbidden:
                    print(f"Cannot send messages in {general_channel.name} ({guild.name})")
                except Exception as e:
                    print(f"Error sending announcement in {guild.name}: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
            else:
                print(f"No suitable channel found in {guild.name}")
    except Exception as e:
        print(f"Error in announce_leaderboard_results: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        session.close()

async def create_new_period(storage, leaderboard_type):
    """Create a new leaderboard period"""
    print(f"Creating new {leaderboard_type.value} period")
    
    session = storage.Session()
    try:
        # Get current time in UTC first
        utc_now = datetime.now(pytz.UTC)
        # Convert to CST
        cst = pytz.timezone('America/Chicago')
        now = utc_now.astimezone(cst)
        
        # Calculate period boundaries in CST
        if leaderboard_type == LeaderboardType.WEEKLY:
            # Start from last Monday 00:00 CST
            days_since_monday = now.weekday()
            period_start = now - timedelta(days=days_since_monday)
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=7)
        else:  # MONTHLY
            # Start from 1st of current month CST
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Create end time
            if now.month == 12:
                period_end = now.replace(year=now.year + 1, month=1, day=1,
                                     hour=0, minute=0, second=0, microsecond=0)
            else:
                period_end = now.replace(month=now.month + 1, day=1,
                                     hour=0, minute=0, second=0, microsecond=0)
        
        # Create the new period
        new_period = LeaderboardPeriod(
            leaderboard_type=leaderboard_type,
            start_time=period_start,
            end_time=period_end,
            is_active=True
        )
        session.add(new_period)
        session.commit()
        
        print(f"Created new {leaderboard_type.value} period: {period_start} to {period_end}")
        return new_period
    finally:
        session.close()

async def get_leaderboard_data(storage, period):
    """Get leaderboard data for a specific period"""
    print(f"Getting leaderboard data for period: {period.start_time} to {period.end_time}")
    
    session = storage.Session()
    try:
        # Get basic stats for the specific period
        print("Querying basic stats...")
        query = session.query(
            GamingSession.user_id,
            func.sum(GamingSession.credits_earned).label('total_credits'),
            func.count(GamingSession.game_id.distinct()).label('games_played')
        ).filter(
            GamingSession.timestamp >= period.start_time,
            GamingSession.timestamp < period.end_time
        )

        results = query.group_by(GamingSession.user_id)\
                     .order_by(func.sum(GamingSession.credits_earned).desc())\
                     .all()

        print(f"Found {len(results)} users with activity in this period")
        if not results:
            print("No activity found in this period")
            return []

        # For each user, get their most played game in the period
        print("Getting most played games for each user...")
        final_results = []
        for user_id, credits, games in results:
            print(f"Processing user {user_id}...")
            # Query to get the most played game for this user
            most_played_query = session.query(
                Game.name,
                func.sum(GamingSession.hours).label('total_hours')
            ).join(GamingSession)\
             .filter(
                GamingSession.user_id == user_id,
                GamingSession.timestamp >= period.start_time,
                GamingSession.timestamp < period.end_time
             )

            most_played_game = most_played_query.group_by(Game.name)\
                .order_by(func.sum(GamingSession.hours).desc())\
                .first()

            game_name = most_played_game.name if most_played_game else "No games"
            game_hours = float(most_played_game.total_hours) if most_played_game else 0.0
            final_results.append((user_id, float(credits or 0), games, game_name, game_hours))
            print(f"User {user_id}: {credits:,.1f} credits, {games} games, most played: {game_name} ({game_hours:,.1f}h)")

        print(f"Processed {len(final_results)} users with activity")
        return final_results
    except Exception as e:
        print(f"Error getting leaderboard data: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return []
    finally:
        session.close()

async def record_leaderboard_placements(storage, period, placements):
    """Record placements for a specific period"""
    print(f"Recording placements for period: {period.start_time} to {period.end_time}")
    
    session = storage.Session()
    try:
        # Start a transaction
        session.begin()
        
        # Check if we already have records for this period
        existing_records = session.query(LeaderboardHistory)\
            .filter(LeaderboardHistory.period_id == period.id)\
            .all()

        if existing_records:
            print(f"Found {len(existing_records)} existing records for this period - updating")
            # Delete existing records for this period
            for record in existing_records:
                session.delete(record)
            session.flush()  # Flush changes but don't commit yet
            
            # Get the current sequence value and max ID
            current_seq = session.execute(text("SELECT last_value FROM leaderboard_history_id_seq")).scalar()
            max_id = session.query(func.max(LeaderboardHistory.id)).scalar() or 0
            
            print(f"Current sequence value: {current_seq}, Max ID: {max_id}")
            
            # If sequence is behind max ID, reset it
            if current_seq <= max_id:
                new_seq = max_id + 1
                print(f"Resetting sequence to {new_seq}")
                session.execute(text(f"ALTER SEQUENCE leaderboard_history_id_seq RESTART WITH {new_seq}"))
                session.flush()

        # Record each placement
        for position, (user_id, credits, games, most_played, most_played_hours) in enumerate(placements, 1):
            try:
                # Get the next sequence value
                next_id = session.execute(text("SELECT nextval('leaderboard_history_id_seq')")).scalar()
                print(f"Using ID {next_id} for placement {position}")
                
            history = LeaderboardHistory(
                    id=next_id,  # Explicitly set the ID
                user_id=user_id,
                period_id=period.id,
                leaderboard_type=period.leaderboard_type,
                placement=position,
                credits=credits,
                games_played=games,
                most_played_game=most_played,
                most_played_hours=most_played_hours,
                timestamp=datetime.now(pytz.timezone('America/Chicago'))
            )
            session.add(history)
            print(f"Recording {position}{storage._get_ordinal_suffix(position)} place: User {user_id} with {credits:,.1f} credits")
            except Exception as e:
                print(f"Error recording placement for user {user_id}: {str(e)}")
                session.rollback()
                raise

        # Commit the transaction
        session.commit()
        print("Successfully recorded all placements")
    except Exception as e:
        print(f"Error recording placements: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

async def process_leaderboard_period(bot, storage, leaderboard_type):
    """Process a leaderboard period: announce results for the most recent inactive period"""
    print(f"\nProcessing {leaderboard_type.value} leaderboard")
    
    session = storage.Session()
    try:
        # First check if we have any periods at all
        total_periods = session.query(LeaderboardPeriod).filter(
            LeaderboardPeriod.leaderboard_type == leaderboard_type
        ).count()
        
        print(f"Total {leaderboard_type.value} periods in database: {total_periods}")
        
        if total_periods == 0:
            print(f"No {leaderboard_type.value} periods found in database. Creating a new one...")
            await create_new_period(storage, leaderboard_type)
            return
        
        # Look for the most recent inactive period
        print(f"Looking for most recent inactive {leaderboard_type.value} period...")
        current_period = session.query(LeaderboardPeriod).filter(
            LeaderboardPeriod.leaderboard_type == leaderboard_type,
            LeaderboardPeriod.is_active == False
        ).order_by(LeaderboardPeriod.end_time.desc()).first()
        
        if not current_period:
            print(f"No inactive {leaderboard_type.value} periods found")
            
            # Check if we have any active periods
            active_period = session.query(LeaderboardPeriod).filter(
                LeaderboardPeriod.leaderboard_type == leaderboard_type,
                LeaderboardPeriod.is_active == True
            ).first()
            
            if active_period:
                print(f"Found active period: {active_period.start_time} to {active_period.end_time}")
                print("This period is still active, no announcement needed")
            else:
                print("No active periods found either. Creating a new period...")
                await create_new_period(storage, leaderboard_type)
            return
        
        print(f"Found most recent inactive period: {current_period.start_time} to {current_period.end_time}")
        
        # For weekly leaderboards, check if this is the most recent inactive period
        if leaderboard_type == LeaderboardType.WEEKLY:
            # Get the current time in CST
            utc_now = datetime.now(pytz.UTC)
            cst = pytz.timezone('America/Chicago')
            now = utc_now.astimezone(cst)
            
            # Check if there's a more recent inactive period
            more_recent_period = session.query(LeaderboardPeriod).filter(
                LeaderboardPeriod.leaderboard_type == LeaderboardType.WEEKLY,
                LeaderboardPeriod.is_active == False,
                LeaderboardPeriod.end_time > current_period.end_time
            ).first()
            
            if more_recent_period:
                print(f"Found more recent inactive period: {more_recent_period.start_time} to {more_recent_period.end_time}")
                print("Skipping this period as it's not the most recent")
                return
        
        # Get leaderboard data
        print("Getting leaderboard data...")
        leaderboard_data = await get_leaderboard_data(storage, current_period)
        
        if not leaderboard_data:
            print("No leaderboard data found for this period")
            return
        
        print(f"Found data for {len(leaderboard_data)} users")
        
        # Record placements if they don't exist
        print("Checking for existing records...")
        existing_records = session.query(LeaderboardHistory).filter(
            LeaderboardHistory.period_id == current_period.id
        ).count()
        
        if existing_records == 0:
            print("No existing records found, recording placements...")
            await record_leaderboard_placements(storage, current_period, leaderboard_data)
        else:
            print(f"Found {existing_records} existing records for this period")
        
        # Announce results
        print("Announcing results...")
        await announce_leaderboard_results(bot, storage, current_period)
        
        print(f"Successfully processed {leaderboard_type.value} leaderboard")
    except Exception as e:
        print(f"Error processing {leaderboard_type.value} leaderboard: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        session.close()

async def main():
    """Main function to process leaderboards"""
    print("Starting leaderboard processing...")
    
    try:
        # Connect to Discord
        print("Connecting to Discord...")
        await bot.start(TOKEN)
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        if 'bot' in locals() and bot.is_ready():
            try:
                print("Closing bot connection...")
                await bot.close()
                print("Bot connection closed")
            except:
                pass

if __name__ == "__main__":
    try:
        print("\nStarting force announcement program...")
        print("Command line arguments:", args)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        print("Program finished") 