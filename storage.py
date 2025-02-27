import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy import create_engine, func, DateTime as sqlalchemy_DateTime
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

    def get_leaderboard_by_timeframe(self, days: Optional[int] = None) -> List[Tuple[int, float, int]]:
        """Get sorted list of (user_id, credits, games_played) tuples for a specific timeframe"""
        session = self.Session()
        try:
            query = session.query(
                GamingSession.user_id,
                func.sum(GamingSession.credits_earned).label('total_credits'),
                func.count(GamingSession.game_id.distinct()).label('games_played')
            )

            if days is not None:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query = query.filter(
                    func.cast(GamingSession.timestamp, sqlalchemy_DateTime) >= cutoff_date
                )

            results = query.group_by(GamingSession.user_id)\
                         .order_by(func.sum(GamingSession.credits_earned).desc())\
                         .all()

            return [(r[0], float(r[1] or 0), r[2]) for r in results]
        finally:
            session.close()

    def get_user_gaming_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's recent gaming sessions with game details"""
        session = self.Session()
        try:
            sessions = session.query(GamingSession, Game)\
                .join(Game)\
                .filter(GamingSession.user_id == user_id)\
                .order_by(GamingSession.timestamp.desc())\
                .limit(limit)\
                .all()

            return [{
                'game': s.Game.name,
                'hours': s.GamingSession.hours,
                'credits_earned': s.GamingSession.credits_earned,
                'timestamp': s.GamingSession.timestamp,
                'rate': s.Game.credits_per_hour
            } for s in sessions]
        finally:
            session.close()

    def get_user_achievements(self, user_id: int) -> Dict[str, bool]:
        """Get user's achievement status"""
        session = self.Session()
        try:
            # Get total stats
            total_credits = self.get_user_credits(user_id)
            total_hours = session.query(func.sum(GamingSession.hours))\
                .filter(GamingSession.user_id == user_id)\
                .scalar() or 0
            unique_games = session.query(func.count(GamingSession.game_id.distinct()))\
                .filter(GamingSession.user_id == user_id)\
                .scalar() or 0

            return {
                'novice_gamer': total_hours >= 10,
                'veteran_gamer': total_hours >= 100,
                'gaming_legend': total_hours >= 1000,
                'credit_collector': total_credits >= 100,
                'credit_hoarder': total_credits >= 1000,
                'game_explorer': unique_games >= 5,
                'game_connoisseur': unique_games >= 20
            }
        finally:
            session.close()

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
            game = session.query(Game).filter(Game.name == game_name).first()
            if not game:
                game = Game(name=game_name, credits_per_hour=1.0, added_by=user_id)
                session.add(game)
                session.commit()

            # Get or create user stats
            user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
            if not user_stats:
                user_stats = UserStats(user_id=user_id, total_credits=0.0)
                session.add(user_stats)
                session.commit()

            # Calculate credits
            credits = hours * game.credits_per_hour

            # Record gaming session
            gaming_session = GamingSession(
                user_id=user_id,
                game_id=game.id,
                hours=hours,
                credits_earned=credits,
                timestamp=datetime.utcnow()  # Store as DateTime object directly
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

    def get_game_stats(self, game_name: str) -> Optional[Dict]:
        """Get detailed statistics for a specific game"""
        session = self.Session()
        try:
            game = session.query(Game).filter(Game.name == game_name).first()
            if not game:
                return None

            # Get total hours and credits for this game
            stats = session.query(
                func.sum(GamingSession.hours).label('total_hours'),
                func.sum(GamingSession.credits_earned).label('total_credits'),
                func.count(GamingSession.id.distinct()).label('total_sessions'),
                func.count(GamingSession.user_id.distinct()).label('unique_players')
            ).filter(GamingSession.game_id == game.id).first()

            return {
                'name': game.name,
                'credits_per_hour': game.credits_per_hour,
                'total_hours': float(stats.total_hours or 0),
                'total_credits': float(stats.total_credits or 0),
                'total_sessions': stats.total_sessions,
                'unique_players': stats.unique_players,
                'added_by': game.added_by
            }
        finally:
            session.close()

    def get_user_game_summaries(self, user_id: int) -> List[Dict]:
        """Get summary of total hours and credits per game for a user"""
        session = self.Session()
        try:
            summaries = session.query(
                Game.name,
                func.sum(GamingSession.hours).label('total_hours'),
                func.sum(GamingSession.credits_earned).label('total_credits'),
                func.count(GamingSession.id).label('sessions'),
                Game.credits_per_hour
            ).join(GamingSession)\
             .filter(GamingSession.user_id == user_id)\
             .group_by(Game.id, Game.name, Game.credits_per_hour)\
             .order_by(func.sum(GamingSession.hours).desc())\
             .all()

            return [{
                'game': s.name,
                'total_hours': float(s.total_hours),
                'total_credits': float(s.total_credits),
                'sessions': s.sessions,
                'rate': s.credits_per_hour
            } for s in summaries]
        finally:
            session.close()

    def get_user_game_stats(self, user_id: int, game_name: str) -> Optional[Dict]:
        """Get detailed statistics for a specific game for a specific user"""
        session = self.Session()
        try:
            game = session.query(Game).filter(Game.name == game_name).first()
            if not game:
                return None

            # Get user-specific stats for this game
            stats = session.query(
                func.sum(GamingSession.hours).label('total_hours'),
                func.sum(GamingSession.credits_earned).label('total_credits'),
                func.count(GamingSession.id).label('total_sessions'),
                func.min(GamingSession.timestamp).label('first_played'),
                func.max(GamingSession.timestamp).label('last_played')
            ).filter(
                GamingSession.game_id == game.id,
                GamingSession.user_id == user_id
            ).first()

            if not stats.total_hours:  # User hasn't played this game
                return None

            return {
                'name': game.name,
                'credits_per_hour': game.credits_per_hour,
                'total_hours': float(stats.total_hours),
                'total_credits': float(stats.total_credits),
                'total_sessions': stats.total_sessions,
                'first_played': stats.first_played,
                'last_played': stats.last_played,
                'added_by': game.added_by
            }
        finally:
            session.close()

    def add_bonus_credits(self, user_id: int, credits: float, reason: str, awarded_by: int) -> float:
        """Add bonus credits to a user's total"""
        session = self.Session()
        try:
            # Get or create user stats
            user_stats = session.query(UserStats).filter(UserStats.user_id == user_id).first()
            if not user_stats:
                user_stats = UserStats(user_id=user_id, total_credits=0.0)
                session.add(user_stats)
                session.commit()

            # Add the bonus credits
            user_stats.total_credits += credits
            session.commit()
            return user_stats.total_credits

        finally:
            session.close()