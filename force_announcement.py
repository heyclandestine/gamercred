import asyncio
import discord
from datetime import datetime, timedelta
import pytz
from storage import GameStorage, get_period_boundaries
from models import LeaderboardType, LeaderboardPeriod, LeaderboardHistory
from sqlalchemy import and_, func, create_engine, text
from dotenv import load_dotenv
import os
import argparse
from models import GamingSession, Game, Bonus

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
        print("Placements found:")
        for p in placements:
            print(f"Placement {p.placement}: User {p.user_id} with {p.credits:,.1f} credits")
        
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
                    print(f"Found member {member.display_name} for user ID {placement.user_id}")
                    break
            
            if not member:
                print(f"WARNING: Could not find member for user ID {placement.user_id}")
            
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
            
            print(f"Adding field for {placement.placement}{suffix} place: {username}")
            embed.add_field(
                name=f"{medal} {placement.placement}{suffix} Place: {username}",
                value=(
                    f"💎 {placement.credits:,.1f} credits earned\n"
                    f"🎮 {placement.games_played} games played\n"
                    f"⏱️ {placement.total_hours:,.1f} total hours\n"
                    f"🏆 Most played: {placement.most_played_game} ({placement.most_played_hours:,.1f}h)"
                ),
                inline=False
            )
        
        print("Created announcement embed")
        
        # Send the announcement only to the guild named 'Kendel Fenner's Test server'
        for guild in bot.guilds:
            if guild.name == "Kendel Fenner's Test server" or guild.name == "Landestine":
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
        cst = pytz.timezone('America/Chicago')
        now = datetime.now(cst)
        if leaderboard_type in [LeaderboardType.WEEKLY, LeaderboardType.MONTHLY]:
            start, end = get_period_boundaries(now, leaderboard_type.value.lower())
        else:
            start = datetime(2020, 1, 1, tzinfo=cst)
            end = datetime(2100, 1, 1, tzinfo=cst)
        new_period = LeaderboardPeriod(
            leaderboard_type=leaderboard_type,
            start_time=start,
            end_time=end,
            is_active=True
        )
        session.add(new_period)
        session.commit()
        print(f"Created new {leaderboard_type.value} period: {start} to {end}")
        return new_period
    finally:
        session.close()

async def record_leaderboard_placements(storage, period, placements):
    """Record placements for the given leaderboard period"""
    print(f"Recording placements for period: {period.start_time} to {period.end_time}")
    session = storage.Session()
    try:
        if session.in_transaction():
            session.rollback()
        session.begin()
        existing_records = session.query(LeaderboardHistory)\
            .filter(LeaderboardHistory.period_id == period.id)\
            .all()
        if existing_records:
            print(f"Found {len(existing_records)} existing records for this period - updating")
            for record in existing_records:
                session.delete(record)
            session.flush()
            current_seq = session.execute(text("SELECT last_value FROM leaderboard_history_id_seq")).scalar()
            max_id = session.query(func.max(LeaderboardHistory.id)).scalar() or 0
            print(f"Current sequence value: {current_seq}, Max ID: {max_id}")
            if current_seq <= max_id:
                new_seq = max_id + 1
                print(f"Resetting sequence to {new_seq}")
                session.execute(text(f"ALTER SEQUENCE leaderboard_history_id_seq RESTART WITH {new_seq}"))
                session.flush()
        for position, (user_id, credits, games, most_played, most_played_hours, total_hours) in enumerate(placements, 1):
            try:
                next_id = session.execute(text("SELECT nextval('leaderboard_history_id_seq')")).scalar()
                print(f"Using ID {next_id} for placement {position}")
                history = LeaderboardHistory(
                    id=next_id,
                    user_id=user_id,
                    period_id=period.id,
                    leaderboard_type=period.leaderboard_type,
                    placement=position,
                    credits=credits,
                    games_played=games,
                    most_played_game=most_played,
                    most_played_hours=most_played_hours,
                    total_hours=total_hours,
                    timestamp=datetime.now(pytz.timezone('America/Chicago'))
                )
                session.add(history)
                print(f"Recording {position}{storage._get_ordinal_suffix(position)} place: User {user_id} with {credits:,.1f} credits")
            except Exception as e:
                print(f"Error recording placement for user {user_id}: {str(e)}")
                session.rollback()
                raise
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
        # Find the most recent inactive period
        period = session.query(LeaderboardPeriod).filter(
            LeaderboardPeriod.leaderboard_type == leaderboard_type,
            LeaderboardPeriod.is_active == False
        ).order_by(LeaderboardPeriod.end_time.desc()).first()
        if not period:
            print(f"No inactive {leaderboard_type.value} periods found.")
            return
        print(f"Found most recent inactive period: {period.start_time} to {period.end_time}")
        # Only announce existing placements, do not recalculate or overwrite
        await announce_leaderboard_results(bot, storage, period)
        print(f"Successfully processed {leaderboard_type.value} leaderboard (announce only, no DB changes)")
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