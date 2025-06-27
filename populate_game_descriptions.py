#!/usr/bin/env python3
"""
Script to populate game descriptions for all existing games in the database.
This script fetches descriptions from the RAWG API and updates the games table.

Usage:
    python populate_game_descriptions.py

Requirements:
    - RAWG_API_KEY environment variable must be set
    - Database connection must be configured
"""

import os
import asyncio
import aiohttp
import time
import re
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Game, Base
from storage import GameStorage

# Load environment variables
load_dotenv()

class GameDescriptionPopulator:
    def __init__(self):
        self.rawg_api_key = os.getenv('RAWG_API_KEY')
        self.rawg_api_url = os.getenv('RAWG_API_URL', 'https://api.rawg.io/api')
        
        if not self.rawg_api_key:
            raise ValueError("RAWG_API_KEY environment variable is not set")
        
        # Initialize database connection
        self.storage = GameStorage()
        self.session = self.storage.Session()
        
        # Statistics
        self.total_games = 0
        self.updated_games = 0
        self.failed_games = 0
        self.skipped_games = 0
        
    def clean_and_truncate_description(self, html_text: str, max_length: int = 2500) -> str:
        """Clean HTML and truncate description text"""
        if not html_text:
            return "No description available."
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        
        # Replace HTML entities
        clean_text = clean_text.replace('&quot;', '"').replace('&#39;', "'").replace('&amp;', '&')
        clean_text = clean_text.replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
        
        # Remove extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Truncate if too long
        if len(clean_text) > max_length:
            clean_text = clean_text[:max_length-3] + "..."
        
        return clean_text
    
    async def fetch_game_description_from_rawg(self, game_name: str) -> Optional[str]:
        """Fetch game description from RAWG API"""
        try:
            async with aiohttp.ClientSession() as session:
                # First, search for the game
                async with session.get(
                    f'{self.rawg_api_url}/games',
                    params={
                        'key': self.rawg_api_key,
                        'search': game_name,
                        'page_size': 1
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data.get('results'):
                            game = data['results'][0]
                            game_id = game.get('id')
                            
                            if game_id:
                                # Get detailed game info including description
                                async with session.get(
                                    f'{self.rawg_api_url}/games/{game_id}',
                                    params={'key': self.rawg_api_key}
                                ) as detail_response:
                                    if detail_response.status == 200:
                                        detail_data = await detail_response.json()
                                        description = detail_data.get('description_raw', '')
                                        return self.clean_and_truncate_description(description)
                            
                            # Fallback to search result description
                            description = game.get('description_raw', '')
                            return self.clean_and_truncate_description(description)
                    
                    return None
        except Exception as e:
            print(f"Error fetching description for '{game_name}': {str(e)}")
            return None
    
    def get_all_games_without_descriptions(self) -> List[Dict[str, Any]]:
        """Get all games that don't have descriptions yet"""
        try:
            # Check if description column exists
            result = self.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'games' AND column_name = 'description'
            """)).fetchone()
            
            if not result:
                print("❌ Description column does not exist in games table!")
                print("Please add the description column first:")
                print("ALTER TABLE games ADD COLUMN description TEXT;")
                return []
            
            # Get all games without descriptions
            games = self.session.query(Game).filter(
                (Game.description.is_(None)) | (Game.description == '')
            ).all()
            
            return [{'id': game.id, 'name': game.name} for game in games]
            
        except Exception as e:
            print(f"Error getting games without descriptions: {str(e)}")
            return []
    
    async def update_game_description(self, game_id: int, game_name: str) -> bool:
        """Update a single game's description"""
        try:
            print(f"🔄 Fetching description for: {game_name}")
            
            # Fetch description from RAWG
            description = await self.fetch_game_description_from_rawg(game_name)
            
            if description:
                # Update the game in the database
                game = self.session.query(Game).filter(Game.id == game_id).first()
                if game:
                    game.description = description
                    self.session.commit()
                    print(f"✅ Updated: {game_name} ({len(description)} chars)")
                    return True
                else:
                    print(f"❌ Game not found in database: {game_name}")
                    return False
            else:
                print(f"⚠️  No description found for: {game_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating {game_name}: {str(e)}")
            self.session.rollback()
            return False
    
    async def populate_all_descriptions(self):
        """Main function to populate descriptions for all games"""
        print("🚀 Starting game description population...")
        print(f"📡 Using RAWG API: {self.rawg_api_url}")
        print(f"🔑 API Key: {'*' * (len(self.rawg_api_key) - 4) + self.rawg_api_key[-4:] if self.rawg_api_key else 'NOT SET'}")
        print()
        
        # Get all games without descriptions
        games_to_update = self.get_all_games_without_descriptions()
        
        if not games_to_update:
            print("✅ All games already have descriptions!")
            return
        
        self.total_games = len(games_to_update)
        print(f"📊 Found {self.total_games} games without descriptions")
        print()
        
        # Process games with rate limiting
        for i, game in enumerate(games_to_update, 1):
            print(f"[{i}/{self.total_games}] ", end="")
            
            success = await self.update_game_description(game['id'], game['name'])
            
            if success:
                self.updated_games += 1
            else:
                self.failed_games += 1
            
            # Rate limiting - wait 1 second between requests to be respectful to RAWG API
            if i < self.total_games:
                print("⏳ Waiting 1 second...")
                await asyncio.sleep(1)
            
            print()
        
        # Print summary
        print("=" * 50)
        print("📈 POPULATION SUMMARY")
        print("=" * 50)
        print(f"Total games processed: {self.total_games}")
        print(f"Successfully updated: {self.updated_games}")
        print(f"Failed to update: {self.failed_games}")
        print(f"Skipped: {self.skipped_games}")
        print(f"Success rate: {(self.updated_games/self.total_games)*100:.1f}%")
        print()
        
        if self.failed_games > 0:
            print("💡 Some games failed to update. This could be due to:")
            print("   - Games not found in RAWG database")
            print("   - API rate limiting")
            print("   - Network issues")
            print("   - Invalid game names")
            print()
            print("You can run this script again to retry failed games.")
    
    def close(self):
        """Clean up database connection"""
        if self.session:
            self.session.close()

async def main():
    """Main entry point"""
    populator = None
    try:
        populator = GameDescriptionPopulator()
        await populator.populate_all_descriptions()
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if populator:
            populator.close()

if __name__ == "__main__":
    asyncio.run(main()) 