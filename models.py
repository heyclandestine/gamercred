from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Game(Base):
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    credits_per_hour = Column(Float, nullable=False, default=1.0)
    added_by = Column(Integer, nullable=False)  # Discord user ID

class UserStats(Base):
    __tablename__ = 'user_stats'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)  # Discord user ID
    total_credits = Column(Float, default=0.0)

class GamingSession(Base):
    __tablename__ = 'gaming_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # Discord user ID
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    hours = Column(Float, nullable=False)
    credits_earned = Column(Float, nullable=False)
    timestamp = Column(String, nullable=False)  # ISO format
    
    game = relationship("Game")
