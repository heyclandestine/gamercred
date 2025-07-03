from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Enum, BigInteger, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class LeaderboardType(enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALLTIME = "alltime"

class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    credits_per_hour = Column(Float, default=1.0)
    half_life_hours = Column(Float, default=None)  # Hours after which CPH is halved, null means no half-life
    added_by = Column(BigInteger)  # User ID who added the game
    backloggd_url = Column(String)
    rawg_id = Column(Integer)
    box_art_url = Column(String)
    release_date = Column(String)  # Store the release date as a string in ISO format
    description = Column(Text)  # Store game descriptions from RAWG API
    gaming_sessions = relationship("GamingSession", back_populates="game")

class UserStats(Base):
    __tablename__ = 'user_stats'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    total_credits = Column(Float, default=0)
    username = Column(String)
    avatar_url = Column(String)
    
    gaming_sessions = relationship("GamingSession", back_populates="user")
    bonuses = relationship("Bonus", back_populates="user")

class GamingSession(Base):
    __tablename__ = 'gaming_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('user_stats.user_id'), nullable=False)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    hours = Column(Float, nullable=False)
    credits_earned = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    players = Column(Integer, nullable=False, default=1)  # Number of players in the session
    
    user = relationship("UserStats", back_populates="gaming_sessions")
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
    user_id = Column(BigInteger, ForeignKey('user_stats.user_id'))  # Changed to BigInteger
    period_id = Column(Integer, ForeignKey('leaderboard_periods.id'))
    leaderboard_type = Column(Enum(LeaderboardType))
    placement = Column(Integer)
    credits = Column(Float)
    games_played = Column(Integer)
    most_played_game = Column(String)
    most_played_hours = Column(Float)
    total_hours = Column(Float)
    timestamp = Column(DateTime)
    period = relationship("LeaderboardPeriod", back_populates="history")

class Bonus(Base):
    __tablename__ = 'bonuses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('user_stats.user_id'), nullable=False)
    credits = Column(Float, nullable=False)
    reason = Column(String, nullable=False)
    granted_by = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    user = relationship("UserStats", back_populates="bonuses")