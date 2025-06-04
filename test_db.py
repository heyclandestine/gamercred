import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pytz
from datetime import datetime

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('LOCAL_DATABASE_URL')
print(f"Testing database connection with URL: {DATABASE_URL}")

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Test connection
    with engine.connect() as connection:
        # Simple test query
        result = connection.execute(text("SELECT 1"))
        print("Database connection successful!")
        
        # List all tables
        result = connection.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name;
        """))
        tables = result.fetchall()
        print("\nTables in database:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Check leaderboard_periods table
        result = connection.execute(text("SELECT COUNT(*) FROM leaderboard_periods"))
        count = result.scalar()
        print(f"\nNumber of leaderboard periods: {count}")
        
        # Get current time in CST
        cst = pytz.timezone('America/Chicago')
        now = datetime.now(cst)
        print(f"\nCurrent time (CST): {now}")
        
        # Check inactive periods
        print("\nInactive periods by type:")
        
        # Weekly inactive periods
        result = connection.execute(text("""
            SELECT id, start_time, end_time, is_active, leaderboard_type
            FROM leaderboard_periods 
            WHERE is_active = 0 AND leaderboard_type = 'WEEKLY'
            ORDER BY end_time DESC
        """))
        periods = result.fetchall()
        print("\nWeekly inactive periods (most recent first):")
        for period in periods:
            print(f"ID: {period[0]}")
            print(f"  Start: {period[1]} CST")
            print(f"  End: {period[2]} CST")
            print()
            
        # Monthly inactive periods
        result = connection.execute(text("""
            SELECT id, start_time, end_time, is_active, leaderboard_type
            FROM leaderboard_periods 
            WHERE is_active = 0 AND leaderboard_type = 'MONTHLY'
            ORDER BY end_time DESC
        """))
        periods = result.fetchall()
        print("\nMonthly inactive periods (most recent first):")
        for period in periods:
            print(f"ID: {period[0]}")
            print(f"  Start: {period[1]} CST")
            print(f"  End: {period[2]} CST")
            print()
            
        # Check leaderboard history
        result = connection.execute(text("SELECT COUNT(*) FROM leaderboard_history"))
        history_count = result.scalar()
        print(f"\nNumber of leaderboard history records: {history_count}")
            
except Exception as e:
    print(f"Error connecting to database: {str(e)}")
    import traceback
    traceback.print_exc() 