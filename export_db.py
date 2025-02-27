
import os
import subprocess
import json
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from models import Base, Game, UserStats, GamingSession

# Load environment variables
load_dotenv()

# Get database URL from environment
database_url = os.getenv('DATABASE_URL')

if not database_url:
    print("ERROR: DATABASE_URL environment variable is not set")
    exit(1)

print(f"Current directory: {os.getcwd()}")
print(f"Database URL found (first 10 chars): {database_url[:10]}...")

try:
    # Connect to the database
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Export data to JSON format
    print("Exporting data to JSON...")
    
    # Get all data
    games = session.query(Game).all()
    user_stats = session.query(UserStats).all()
    gaming_sessions = session.query(GamingSession).all()
    
    # Convert to dictionaries
    games_data = [
        {
            'id': g.id,
            'name': g.name,
            'credits_per_hour': g.credits_per_hour,
            'added_by': g.added_by
        } for g in games
    ]
    
    user_stats_data = [
        {
            'id': u.id,
            'user_id': u.user_id,
            'total_credits': u.total_credits
        } for u in user_stats
    ]
    
    gaming_sessions_data = [
        {
            'id': s.id,
            'user_id': s.user_id,
            'game_id': s.game_id,
            'hours': s.hours,
            'credits_earned': s.credits_earned,
            'timestamp': s.timestamp.isoformat() if s.timestamp else None
        } for s in gaming_sessions
    ]
    
    # Combine all data
    all_data = {
        'games': games_data,
        'user_stats': user_stats_data,
        'gaming_sessions': gaming_sessions_data,
        'export_date': datetime.now().isoformat(),
        'database_source': 'Replit PostgreSQL'
    }
    
    # Write to file
    export_file = 'database_export.json'
    with open(export_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"✅ Data successfully exported to {export_file}")
    print(f"File size: {os.path.getsize(export_file)} bytes")
    print(f"Record counts: {len(games_data)} games, {len(user_stats_data)} user stats, {len(gaming_sessions_data)} gaming sessions")
    print("\nTo download this file, locate it in the Replit file explorer and right-click to download.")
    
except Exception as e:
    print(f"❌ Error exporting database: {e}")
    exit(1)
