import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Game, UserStats, GamingSession

class GameStorage:
    def __init__(self):
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_or_create_game(self, game_name: str, user_id: int, credits_per_hour: float = 1.0) -> Tuple[Game, bool]:
        """Get a game by name or create it if it doesn't exist"""
        session = self.Session()
        try:
            game = session.query(Game).filter(Game.name == game_name).first()
            if not game:
                game = Game(name=game_name, credits_per_hour=credits_per_hour, added_by=user_id)
                session.add(game)
                session.commit()
                return game, True
            return game, False
        finally:
            session.close()

    def set_game_credits_per_hour(self, game_name: str, credits: float, user_id: int) -> bool:
        """Set credits per hour for a game"""
        if not 0.1 <= credits <= 10.0:  # Reasonable limits
            return False

        session = self.Session()
        try:
            # Look for existing game first
            game = session.query(Game).filter(Game.name == game_name).first()

            if game:
                # Update existing game
                game.credits_per_hour = credits
            else:
                # Create new game with specified rate
                game = Game(name=game_name, credits_per_hour=credits, added_by=user_id)
                session.add(game)

            session.commit()
            return True
        finally:
            session.close()

    def add_gaming_hours(self, user_id: int, hours: float, game_name: str) -> float:
        """Add gaming hours and return earned credits"""
        session = self.Session()
        try:
            # Get or create game
            game, _ = self.get_or_create_game(game_name, user_id)

            # Get or create user stats
            user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
            if not user_stats:
                user_stats = UserStats(user_id=user_id)
                session.add(user_stats)

            # Calculate credits
            credits = hours * game.credits_per_hour

            # Record gaming session
            gaming_session = GamingSession(
                user_id=user_id,
                game_id=game.id,
                hours=hours,
                credits_earned=credits,
                timestamp=datetime.utcnow().isoformat()
            )
            session.add(gaming_session)

            # Update user's total credits
            user_stats.total_credits += credits

            session.commit()
            return credits
        finally:
            session.close()

    def get_user_credits(self, user_id: int) -> float:
        """Get user's total credits"""
        session = self.Session()
        try:
            user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
            return user_stats.total_credits if user_stats else 0.0
        finally:
            session.close()

    def get_leaderboard(self) -> List[Tuple[int, float]]:
        """Get sorted list of (user_id, credits) tuples"""
        session = self.Session()
        try:
            users = session.query(UserStats).order_by(UserStats.total_credits.desc()).all()
            return [(user.user_id, user.total_credits) for user in users]
        finally:
            session.close()

    def get_game_info(self, game_name: str) -> Optional[Dict]:
        """Get game information including credits per hour"""
        session = self.Session()
        try:
            game = session.query(Game).filter(Game.name == game_name).first()
            if game:
                return {
                    'name': game.name,
                    'credits_per_hour': game.credits_per_hour,
                    'added_by': game.added_by
                }
            return None
        finally:
            session.close()