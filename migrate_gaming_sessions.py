import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Get database URL from environment variables
database_url = os.getenv('DATABASE_URL') or os.getenv('LOCAL_DATABASE_URL')
if not database_url:
    raise ValueError("No database URL found. Set DATABASE_URL or LOCAL_DATABASE_URL environment variable")

print(f"Connecting to database: {database_url}")

# Create the database engine
engine = create_engine(database_url)

def migrate_gaming_sessions():
    """Migrate the gaming_sessions table to use autoincrement"""
    try:
        with engine.connect() as conn:
            # Start a transaction
            with conn.begin():
                # 1. Create a temporary table with the correct schema
                print("Creating temporary table...")
                conn.execute(text("""
                    CREATE TABLE gaming_sessions_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        game_id INTEGER,
                        hours FLOAT,
                        credits_earned FLOAT,
                        timestamp DATETIME,
                        FOREIGN KEY (user_id) REFERENCES user_stats(user_id),
                        FOREIGN KEY (game_id) REFERENCES games(id)
                    )
                """))

                # 2. Copy data from the old table to the new one
                print("Copying data to temporary table...")
                conn.execute(text("""
                    INSERT INTO gaming_sessions_temp (user_id, game_id, hours, credits_earned, timestamp)
                    SELECT user_id, game_id, hours, credits_earned, timestamp
                    FROM gaming_sessions
                """))

                # 3. Drop the old table
                print("Dropping old table...")
                conn.execute(text("DROP TABLE gaming_sessions"))

                # 4. Rename the temporary table to the original name
                print("Renaming temporary table...")
                conn.execute(text("ALTER TABLE gaming_sessions_temp RENAME TO gaming_sessions"))

                print("Migration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {str(e)}")
        raise

if __name__ == '__main__':
    migrate_gaming_sessions() 