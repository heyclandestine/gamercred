
import os
import json
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Game, UserStats, GamingSession
from datetime import datetime

def import_data(database_url, json_file):
    print(f"Connecting to database: {database_url}")
    print(f"Importing data from: {json_file}")
    
    # Connect to the database
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Import games
    print(f"Importing {len(data['games'])} games...")
    for game_data in data['games']:
        game = Game(
            id=game_data['id'],
            name=game_data['name'],
            credits_per_hour=game_data['credits_per_hour'],
            added_by=game_data['added_by']
        )
        session.merge(game)  # Use merge instead of add to handle existing records
    
    # Import user stats
    print(f"Importing {len(data['user_stats'])} user stats...")
    for stats_data in data['user_stats']:
        user_stats = UserStats(
            id=stats_data['id'],
            user_id=stats_data['user_id'],
            total_credits=stats_data['total_credits']
        )
        session.merge(user_stats)
    
    # Import gaming sessions
    print(f"Importing {len(data['gaming_sessions'])} gaming sessions...")
    for session_data in data['gaming_sessions']:
        # Convert timestamp string to datetime if it exists
        timestamp = None
        if session_data['timestamp']:
            timestamp = datetime.fromisoformat(session_data['timestamp'])
            
        gaming_session = GamingSession(
            id=session_data['id'],
            user_id=session_data['user_id'],
            game_id=session_data['game_id'],
            hours=session_data['hours'],
            credits_earned=session_data['credits_earned'],
            timestamp=timestamp
        )
        session.merge(gaming_session)
    
    # Commit changes
    session.commit()
    print("Import complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_db.py DATABASE_URL [JSON_FILE]")
        print("Example: python import_db.py postgresql://username:password@localhost/gamer_cred database_export.json")
        sys.exit(1)
    
    database_url = sys.argv[1]
    json_file = sys.argv[2] if len(sys.argv) > 2 else "database_export.json"
    
    import_data(database_url, json_file)
