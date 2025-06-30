#!/usr/bin/env python3
"""
Migration script to add half_life_hours column to games table.
This enables the half-life system for CPH calculation.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import our models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Base

def migrate_add_half_life():
    """Add half_life_hours column to games table"""
    
    # Create engine - adjust the database URL as needed
    database_url = os.getenv('DATABASE_URL', 'sqlite:///gamercred.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url)
    
    try:
        # Check if the column already exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'games' AND column_name = 'half_life_hours'
            """))
            
            if result.fetchone():
                print("Column 'half_life_hours' already exists in games table.")
                return
        
        # Add the column
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE games 
                ADD COLUMN half_life_hours FLOAT DEFAULT NULL
            """))
            conn.commit()
            
        print("Successfully added 'half_life_hours' column to games table.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        raise

if __name__ == "__main__":
    migrate_add_half_life() 