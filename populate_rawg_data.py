import os
import asyncio
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import GameStorage # Import GameStorage
from models import Game, Base # Import Game and Base

# Load environment variables (including RAWG_API_KEY and LOCAL_DATABASE_URL)
# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the .env file in the project root
env_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=env_path)

# Define the database path - make sure this matches the path in your backend/app.py
# Use the environment variable for consistency
DATABASE_URL = os.getenv('LOCAL_DATABASE_URL')
if not DATABASE_URL:
    # Fallback to the hardcoded path if env var is not set, but recommend using env var
    DATABASE_PATH = 'C:/Users/kende/Downloads/DiscordCompanion/gamer_cred.db'
    print(f"LOCAL_DATABASE_URL env var not set. Using hardcoded path: {DATABASE_PATH}")
    DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# Debug print the database URL being used
print(f"Debug: Database URL being used: {DATABASE_URL}")

# Initialize the GameStorage instance
storage = GameStorage()

async def populate_rawg_data_for_existing_games():
    """Fetches and populates RAWG data for all games in the database."""
    # Use the session maker from GameStorage
    Session = storage.Session
    session = Session()

    try:
        print("Starting RAWG data population for all games...")

        # Get all games
        all_games = session.query(Game).all()
        print(f"Debug: Total games found in database: {len(all_games)}")

        # Debug print values for first few games
        for i, game in enumerate(all_games[:5]):
            print(f"Debug: Game {i+1}: {game.name}, rawg_id: {game.rawg_id}, box_art_url: {game.box_art_url}")

        print(f"Found {len(all_games)} games to update.")

        for game in all_games:
            print(f"Processing game: {game.name}")
            
            # Fetch details from RAWG
            rawg_details = await storage.fetch_game_details_from_rawg(game.name)

            if rawg_details:
                # Update game object with fetched data
                game.rawg_id = rawg_details.get('rawg_id')
                game.box_art_url = rawg_details.get('box_art_url')

                # Commit changes for this game
                session.add(game)
                session.commit()
                print(f"  Successfully updated RAWG data for {game.name}.")
            else:
                print(f"  Failed to fetch RAWG data for {game.name}. Skipping update.")

        print("RAWG data population script finished.")

    except Exception as e:
        print(f"An error occurred during RAWG data population: {e}")
        session.rollback() # Roll back changes in case of error
    finally:
        session.close() # Close the session

if __name__ == "__main__":
    # Ensure aiohttp is installed for async http requests
    try:
        import aiohttp
    except ImportError:
        print("The 'aiohttp' library is required. Please install it:")
        print("pip install aiohttp")
        sys.exit(1)

    # Run the asynchronous population function
    asyncio.run(populate_rawg_data_for_existing_games())