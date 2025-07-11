#!/usr/bin/env python3
"""
Migration script to add game interactivity tables:
- game_reviews
- game_ratings  
- game_completions
- game_screenshots
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_tables():
    """Create the new game interactivity tables using raw SQL"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Create game_reviews table
        print("Creating game_reviews table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_reviews (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES user_stats(user_id),
                game_id INTEGER NOT NULL REFERENCES games(id),
                review_text TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        # Create game_ratings table
        print("Creating game_ratings table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_ratings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES user_stats(user_id),
                game_id INTEGER NOT NULL REFERENCES games(id),
                rating FLOAT NOT NULL CHECK (rating >= 0.5 AND rating <= 5.0),
                timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, game_id)
            )
        """)
        
        # Create game_completions table
        print("Creating game_completions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_completions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES user_stats(user_id),
                game_id INTEGER NOT NULL REFERENCES games(id),
                completed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                credits_awarded FLOAT DEFAULT 1000.0,
                UNIQUE(user_id, game_id)
            )
        """)
        
        # Create game_screenshots table
        print("Creating game_screenshots table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_screenshots (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES user_stats(user_id),
                game_id INTEGER NOT NULL REFERENCES games(id),
                image_url VARCHAR NOT NULL,
                caption VARCHAR,
                uploaded_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        
        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Successfully created game interactivity tables:")
        print("   - game_reviews")
        print("   - game_ratings")
        print("   - game_completions") 
        print("   - game_screenshots")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False

def verify_tables():
    """Verify that the tables were created successfully"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check if tables exist
        tables_to_check = ['game_reviews', 'game_ratings', 'game_completions', 'game_screenshots']
        
        for table in tables_to_check:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table,))
            exists = cursor.fetchone()[0]
            
            if exists:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' does not exist")
                return False
        
        cursor.close()
        conn.close()
        
        print("✅ All game interactivity tables verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying tables: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting game interactivity tables migration...")
    
    # Create tables
    if create_tables():
        # Verify tables
        verify_tables()
    else:
        print("❌ Migration failed!")
        sys.exit(1) 