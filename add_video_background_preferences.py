#!/usr/bin/env python3
"""
Migration script to add video background support to user_preferences table.
Run this script to add the new columns for video backgrounds.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import storage
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate_database():
    """Add video background columns to user_preferences table."""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL', 'sqlite:///gaming_credits.db')
    
    print(f"Connecting to database: {database_url}")
    
    # Create engine
    engine = create_engine(database_url)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if columns already exist
        result = session.execute(text("PRAGMA table_info(user_preferences)"))
        columns = [row[1] for row in result.fetchall()]
        
        print(f"Existing columns: {columns}")
        
        # Add background_video_url column if it doesn't exist
        if 'background_video_url' not in columns:
            print("Adding background_video_url column...")
            session.execute(text("ALTER TABLE user_preferences ADD COLUMN background_video_url TEXT"))
            print("✓ Added background_video_url column")
        else:
            print("✓ background_video_url column already exists")
        
        # Add background_type column if it doesn't exist
        if 'background_type' not in columns:
            print("Adding background_type column...")
            session.execute(text("ALTER TABLE user_preferences ADD COLUMN background_type TEXT DEFAULT 'image'"))
            print("✓ Added background_type column")
        else:
            print("✓ background_type column already exists")
        
        # Commit changes
        session.commit()
        print("\n✅ Migration completed successfully!")
        
        # Show final table structure
        print("\nFinal table structure:")
        result = session.execute(text("PRAGMA table_info(user_preferences)"))
        for row in result.fetchall():
            print(f"  {row[1]} ({row[2]}) - Default: {row[4]}")
            
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("🎬 Adding video background support to user_preferences table...")
    migrate_database() 