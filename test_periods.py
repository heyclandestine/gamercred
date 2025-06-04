import os
import asyncio
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pytz
from datetime import datetime, timedelta
from models import LeaderboardPeriod, LeaderboardType
from storage import GameStorage
import discord

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('LOCAL_DATABASE_URL')
print(f"Testing period transitions with database URL: {DATABASE_URL}")

def print_periods(connection, period_type):
    """Print all periods of a given type"""
    result = connection.execute(text(f"""
        SELECT id, start_time, end_time, is_active, leaderboard_type
        FROM leaderboard_periods 
        WHERE leaderboard_type = '{period_type}'
        ORDER BY end_time DESC
    """))
    periods = result.fetchall()
    print(f"\n{period_type} periods (most recent first):")
    for period in periods:
        print(f"ID: {period[0]}")
        print(f"  Start: {period[1]} CST")
        print(f"  End: {period[2]} CST")
        print(f"  Active: {period[3]}")
        print()

async def test_period_transition():
    """Test the period transition logic"""
    try:
        # Create storage instance
        storage = GameStorage()
        
        # Get current time in CST
        cst = pytz.timezone('America/Chicago')
        now = datetime.now(cst)
        print(f"\nCurrent time (CST): {now}")
        
        # Create engine for direct database access
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            # Print initial state
            print("\nInitial state:")
            print_periods(connection, 'WEEKLY')
            print_periods(connection, 'MONTHLY')
            
            # Test weekly transition
            print("\nTesting weekly transition...")
            weekly_period = await storage.get_or_create_current_period(LeaderboardType.WEEKLY)
            if weekly_period:
                # Force end time to now
                weekly_period.end_time = now
                session = storage.Session()
                try:
                    session.commit()
                finally:
                    session.close()
            
            # Test monthly transition
            print("\nTesting monthly transition...")
            monthly_period = await storage.get_or_create_current_period(LeaderboardType.MONTHLY)
            if monthly_period:
                # Force end time to now
                monthly_period.end_time = now
                session = storage.Session()
                try:
                    session.commit()
                finally:
                    session.close()
            
            # Run the check_periods task
            print("\nRunning check_periods task...")
            from commands import GamingCommands
            from discord.ext import commands
            
            # Set up bot with intents
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            bot = commands.Bot(command_prefix='!', intents=intents)
            
            gaming_commands = GamingCommands(bot)
            await gaming_commands.check_periods()
            
            # Print final state
            print("\nFinal state:")
            print_periods(connection, 'WEEKLY')
            print_periods(connection, 'MONTHLY')
            
    except Exception as e:
        print(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_period_transition()) 