#!/usr/bin/env python3
"""
Migration script to add background image preferences to user_preferences table.
Run this script to add the new columns to your existing database.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print(f"Connecting to database: {database_url}")
    
    # Create engine
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_preferences' 
                AND column_name IN ('background_image_url', 'background_opacity')
            """))
            existing_columns = [row[0] for row in result]
            
            if 'background_image_url' not in existing_columns:
                print("Adding background_image_url column...")
                conn.execute(text("""
                    ALTER TABLE user_preferences 
                    ADD COLUMN background_image_url VARCHAR
                """))
                print("✓ Added background_image_url column")
            else:
                print("✓ background_image_url column already exists")
            
            if 'background_opacity' not in existing_columns:
                print("Adding background_opacity column...")
                conn.execute(text("""
                    ALTER TABLE user_preferences 
                    ADD COLUMN background_opacity FLOAT DEFAULT 0.3
                """))
                print("✓ Added background_opacity column")
            else:
                print("✓ background_opacity column already exists")
            
            # Commit the changes
            conn.commit()
            print("\nMigration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration() 