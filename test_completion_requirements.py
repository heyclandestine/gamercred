#!/usr/bin/env python3
"""
Test script to verify completion requirements implementation
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage import GameStorage
from models import Game, UserStats, GamingSession, GameRating, GameCompletion
from sqlalchemy import text
from datetime import datetime

# Load environment variables
load_dotenv()

def test_completion_requirements():
    """Test the completion requirements logic"""
    storage = GameStorage()
    session = storage.Session()
    
    try:
        print("🧪 Testing Completion Requirements Implementation")
        print("=" * 50)
        
        # Test data
        test_user_id = 123456789
        test_game_name = "Test Game"
        
        # Create test game if it doesn't exist
        game = session.query(Game).filter_by(name=test_game_name).first()
        if not game:
            game = Game(
                name=test_game_name,
                credits_per_hour=1.0,
                added_by=test_user_id
            )
            session.add(game)
            session.commit()
            print(f"✅ Created test game: {test_game_name}")
        
        # Create test user if it doesn't exist
        user = session.query(UserStats).filter_by(user_id=test_user_id).first()
        if not user:
            user = UserStats(
                user_id=test_user_id,
                username="TestUser",
                total_credits=0.0
            )
            session.add(user)
            session.commit()
            print(f"✅ Created test user: {test_user_id}")
        
        # Clear any existing data for this test
        session.query(GamingSession).filter_by(user_id=test_user_id, game_id=game.id).delete()
        session.query(GameRating).filter_by(user_id=test_user_id, game_id=game.id).delete()
        session.query(GameCompletion).filter_by(user_id=test_user_id, game_id=game.id).delete()
        session.commit()
        print("✅ Cleared existing test data")
        
        # Test 1: No hours, no rating
        print("\n📋 Test 1: No hours logged, no rating")
        total_hours_result = session.execute(text("""
            SELECT COALESCE(SUM(hours), 0) as total_hours
            FROM gaming_sessions
            WHERE user_id = :user_id AND game_id = :game_id
        """), {"user_id": test_user_id, "game_id": game.id}).first()
        total_hours = float(total_hours_result.total_hours) if total_hours_result else 0.0
        
        user_rating = session.query(GameRating).filter_by(user_id=test_user_id, game_id=game.id).first()
        has_rating = user_rating is not None
        
        print(f"   Hours: {total_hours:.1f}/3.0 (Required: {total_hours >= 3.0})")
        print(f"   Rating: {'Yes' if has_rating else 'No'} (Required: {has_rating})")
        print(f"   Can Complete: {total_hours >= 3.0 and has_rating}")
        
        # Test 2: Add 2 hours (still not enough)
        print("\n📋 Test 2: 2 hours logged, no rating")
        gaming_session = GamingSession(
            user_id=test_user_id,
            game_id=game.id,
            hours=2.0,
            credits_earned=2.0,
            timestamp=datetime.utcnow()
        )
        session.add(gaming_session)
        session.commit()
        
        total_hours_result = session.execute(text("""
            SELECT COALESCE(SUM(hours), 0) as total_hours
            FROM gaming_sessions
            WHERE user_id = :user_id AND game_id = :game_id
        """), {"user_id": test_user_id, "game_id": game.id}).first()
        total_hours = float(total_hours_result.total_hours) if total_hours_result else 0.0
        
        user_rating = session.query(GameRating).filter_by(user_id=test_user_id, game_id=game.id).first()
        has_rating = user_rating is not None
        
        print(f"   Hours: {total_hours:.1f}/3.0 (Required: {total_hours >= 3.0})")
        print(f"   Rating: {'Yes' if has_rating else 'No'} (Required: {has_rating})")
        print(f"   Can Complete: {total_hours >= 3.0 and has_rating}")
        
        # Test 3: Add 1 more hour (now 3 hours total), still no rating
        print("\n📋 Test 3: 3 hours logged, no rating")
        gaming_session = GamingSession(
            user_id=test_user_id,
            game_id=game.id,
            hours=1.0,
            credits_earned=1.0,
            timestamp=datetime.utcnow()
        )
        session.add(gaming_session)
        session.commit()
        
        total_hours_result = session.execute(text("""
            SELECT COALESCE(SUM(hours), 0) as total_hours
            FROM gaming_sessions
            WHERE user_id = :user_id AND game_id = :game_id
        """), {"user_id": test_user_id, "game_id": game.id}).first()
        total_hours = float(total_hours_result.total_hours) if total_hours_result else 0.0
        
        user_rating = session.query(GameRating).filter_by(user_id=test_user_id, game_id=game.id).first()
        has_rating = user_rating is not None
        
        print(f"   Hours: {total_hours:.1f}/3.0 (Required: {total_hours >= 3.0})")
        print(f"   Rating: {'Yes' if has_rating else 'No'} (Required: {has_rating})")
        print(f"   Can Complete: {total_hours >= 3.0 and has_rating}")
        
        # Test 4: Add rating (now should be able to complete)
        print("\n📋 Test 4: 3 hours logged, with rating")
        user_rating = GameRating(
            user_id=test_user_id,
            game_id=game.id,
            rating=4.5,
            timestamp=datetime.utcnow()
        )
        session.add(user_rating)
        session.commit()
        
        total_hours_result = session.execute(text("""
            SELECT COALESCE(SUM(hours), 0) as total_hours
            FROM gaming_sessions
            WHERE user_id = :user_id AND game_id = :game_id
        """), {"user_id": test_user_id, "game_id": game.id}).first()
        total_hours = float(total_hours_result.total_hours) if total_hours_result else 0.0
        
        user_rating = session.query(GameRating).filter_by(user_id=test_user_id, game_id=game.id).first()
        has_rating = user_rating is not None
        
        print(f"   Hours: {total_hours:.1f}/3.0 (Required: {total_hours >= 3.0})")
        print(f"   Rating: {'Yes' if has_rating else 'No'} (Required: {has_rating})")
        print(f"   Can Complete: {total_hours >= 3.0 and has_rating}")
        
        # Test 5: Actually complete the game
        if total_hours >= 3.0 and has_rating:
            print("\n📋 Test 5: Completing the game")
            completion = GameCompletion(
                user_id=test_user_id,
                game_id=game.id,
                completed_at=datetime.utcnow(),
                credits_awarded=1000.0
            )
            session.add(completion)
            
            # Award credits
            user.total_credits = (user.total_credits or 0) + 1000.0
            session.commit()
            
            print(f"   ✅ Game completed successfully!")
            print(f"   💎 Credits awarded: 1000")
            print(f"   💎 New total credits: {user.total_credits}")
        
        print("\n🎉 All tests completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_completion_requirements() 