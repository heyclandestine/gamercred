#!/usr/bin/env python3
"""
Migration script to add new columns to UserPreferences table for storing file data in the database.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_user_preferences():
    """Add new columns to UserPreferences table for storing file data."""
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        # Create database engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_preferences' 
                AND column_name IN (
                    'background_image_data', 
                    'background_video_data', 
                    'background_image_filename', 
                    'background_video_filename',
                    'background_image_mime_type',
                    'background_video_mime_type'
                )
            """))
            
            existing_columns = [row[0] for row in result]
            
            # Add new columns if they don't exist
            new_columns = [
                ('background_image_data', 'TEXT'),
                ('background_video_data', 'TEXT'),
                ('background_image_filename', 'VARCHAR'),
                ('background_video_filename', 'VARCHAR'),
                ('background_image_mime_type', 'VARCHAR'),
                ('background_video_mime_type', 'VARCHAR')
            ]
            
            for column_name, column_type in new_columns:
                if column_name not in existing_columns:
                    print(f"Adding column: {column_name}")
                    conn.execute(text(f"ALTER TABLE user_preferences ADD COLUMN {column_name} {column_type}"))
                    conn.commit()
                else:
                    print(f"Column {column_name} already exists")
            
            print("✅ Migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Starting UserPreferences migration...")
    success = migrate_user_preferences()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1) 