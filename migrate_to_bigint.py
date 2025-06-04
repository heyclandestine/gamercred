from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine
engine = create_engine(DATABASE_URL)

# Migration SQL
migration_sql = """
-- First, ensure all user_id values are valid numbers
UPDATE user_stats SET user_id = NULL WHERE user_id !~ '^[0-9]+$';
UPDATE gaming_sessions SET user_id = NULL WHERE user_id !~ '^[0-9]+$';
UPDATE leaderboard_history SET user_id = NULL WHERE user_id !~ '^[0-9]+$';
UPDATE bonuses SET user_id = NULL WHERE user_id !~ '^[0-9]+$';
UPDATE bonuses SET granted_by = NULL WHERE granted_by !~ '^[0-9]+$';

-- Drop foreign key constraints
ALTER TABLE gaming_sessions DROP CONSTRAINT IF EXISTS gaming_sessions_user_id_fkey;
ALTER TABLE leaderboard_history DROP CONSTRAINT IF EXISTS leaderboard_history_user_id_fkey;
ALTER TABLE bonuses DROP CONSTRAINT IF EXISTS bonuses_user_id_fkey;

-- Alter columns to BIGINT
ALTER TABLE user_stats ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
ALTER TABLE gaming_sessions ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
ALTER TABLE leaderboard_history ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
ALTER TABLE bonuses ALTER COLUMN user_id TYPE BIGINT USING user_id::bigint;
ALTER TABLE bonuses ALTER COLUMN granted_by TYPE BIGINT USING granted_by::bigint;

-- Re-add foreign key constraints
ALTER TABLE gaming_sessions ADD CONSTRAINT gaming_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES user_stats(user_id);
ALTER TABLE leaderboard_history ADD CONSTRAINT leaderboard_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES user_stats(user_id);
ALTER TABLE bonuses ADD CONSTRAINT bonuses_user_id_fkey FOREIGN KEY (user_id) REFERENCES user_stats(user_id);
"""

def run_migration():
    with engine.connect() as connection:
        # Start transaction
        with connection.begin():
            print("Starting migration...")
            
            # Execute migration SQL
            connection.execute(text(migration_sql))
            
            print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration() 