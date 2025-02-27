
import json
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Create the ORM models directly in this file to avoid import issues
from sqlalchemy import Column, Integer, String, Float, ForeignKey, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    credits_per_hour = Column(Float, nullable=False, default=1.0)
    added_by = Column(BigInteger, nullable=False)  # Discord user ID

class UserStats(Base):
    __tablename__ = 'user_stats'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)  # Discord user ID
    total_credits = Column(Float, default=0.0)

class GamingSession(Base):
    __tablename__ = 'gaming_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)  # Discord user ID
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    hours = Column(Float, nullable=False)
    credits_earned = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)  # Changed from String to DateTime

    game = relationship("Game")

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
        else:
            # Use current time if timestamp is missing
            timestamp = datetime.utcnow()
            
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
        print("Usage: python local_import.py DATABASE_URL [JSON_FILE]")
        print("Example: python local_import.py postgresql://postgres:password@localhost:5432/gamer_cred database_export.json")
        sys.exit(1)
    
    database_url = sys.argv[1]
    json_file = sys.argv[2] if len(sys.argv) > 2 else "database_export.json"
    
    import_data(database_url, json_file)
