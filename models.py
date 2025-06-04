from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Enum, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class LeaderboardType(enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    credits_per_hour = Column(Float, default=1.0)
    added_by = Column(BigInteger)  # User ID who added the game
    backloggd_url = Column(String)
    rawg_id = Column(Integer)
    box_art_url = Column(String)
    gaming_sessions = relationship("GamingSession", back_populates="game")

class UserStats(Base):
    __tablename__ = 'user_stats'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True)  # Store as string to preserve precision
    total_credits = Column(Float, default=0.0)
    gaming_sessions = relationship("GamingSession", back_populates="user_stats")
    username = Column(String, nullable=True)      # Discord username
    avatar_url = Column(String, nullable=True)    # (Optional) Discord avatar URL

class GamingSession(Base):
    __tablename__ = 'gaming_sessions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('user_stats.user_id'))  # Changed to String
    game_id = Column(Integer, ForeignKey('games.id'))
    hours = Column(Float)
    credits_earned = Column(Float)
    timestamp = Column(DateTime)
    user_stats = relationship("UserStats", back_populates="gaming_sessions")
    game = relationship("Game", back_populates="gaming_sessions")

class LeaderboardPeriod(Base):
    __tablename__ = 'leaderboard_periods'
    id = Column(Integer, primary_key=True)
    leaderboard_type = Column(Enum(LeaderboardType))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    is_active = Column(Boolean, default=True)
    history = relationship("LeaderboardHistory", back_populates="period")

class LeaderboardHistory(Base):
    __tablename__ = 'leaderboard_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('user_stats.user_id'))  # Changed to String
    period_id = Column(Integer, ForeignKey('leaderboard_periods.id'))
    leaderboard_type = Column(Enum(LeaderboardType))
    placement = Column(Integer)
    credits = Column(Float)
    games_played = Column(Integer)
    most_played_game = Column(String)
    most_played_hours = Column(Float)
    timestamp = Column(DateTime)
    period = relationship("LeaderboardPeriod", back_populates="history")

class Bonus(Base):
    __tablename__ = 'bonuses'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('user_stats.user_id'))  # Changed to String
    credits = Column(Float)
    reason = Column(String)
    granted_by = Column(String)  # Changed to String
    timestamp = Column(DateTime)