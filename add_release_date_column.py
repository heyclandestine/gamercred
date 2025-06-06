import os
import asyncio
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import sys
import time

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import GameStorage
from models import Game, Base

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=env_path)

# Initialize the GameStorage instance
storage = GameStorage()

async def add_release_date_column():
    """Adds release_date column to the games table and populates it with RAWG data."""
    session = storage.Session()
    try:
        print("Starting release date column addition and population...")

        # First, check if the column exists
        inspector = inspect(storage.engine)
        columns = [col['name'] for col in inspector.get_columns('games')]
        
        if 'release_date' not in columns:
            print("Adding release_date column to games table...")
            session.execute(text("ALTER TABLE games ADD COLUMN release_date VARCHAR"))
            session.commit()
            print("Column added successfully.")

        # Get all games
        all_games = session.query(Game).all()
        print(f"Found {len(all_games)} games to update.")

        for i, game in enumerate(all_games, 1):
            print(f"Processing game {i}/{len(all_games)}: {game.name}")
            
            # Skip if release date already exists
            if game.release_date:
                print(f"  Release date already exists for {game.name}: {game.release_date}")
                continue
            
            # Fetch details from RAWG
            rawg_details = await storage.fetch_game_details_from_rawg(game.name)

            if rawg_details and rawg_details.get('release_date'):
                # Update game object with release date
                game.release_date = rawg_details['release_date']
                session.add(game)
                session.commit()
                print(f"  Successfully updated release date for {game.name}: {game.release_date}")
            else:
                print(f"  Failed to fetch release date for {game.name}. Skipping update.")
            
            # Add a small delay to avoid hitting RAWG API rate limits
            await asyncio.sleep(0.5)

        print("Release date column population script finished.")

    except Exception as e:
        print(f"An error occurred during release date population: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(add_release_date_column()) 