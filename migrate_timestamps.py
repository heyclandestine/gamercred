import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table"""
    result = conn.execute(text(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' 
        AND column_name = '{column_name}'
    """))
    return result.scalar() is not None

def migrate_timestamps():
    """Migrate timestamps in gaming_sessions table to CST"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            with conn.begin():
                logger.info("Starting timestamp migration...")
                
                # Check if timestamp_cst already exists
                if not column_exists(conn, 'gaming_sessions', 'timestamp_cst'):
                    # Add new timestamp column
                    logger.info("Adding new timestamp_cst column...")
                    conn.execute(text("""
                        ALTER TABLE gaming_sessions 
                        ADD COLUMN timestamp_cst TIMESTAMP WITH TIME ZONE
                    """))
                else:
                    logger.info("timestamp_cst column already exists, skipping creation...")
                
                # Update timestamps to CST
                logger.info("Converting timestamps to CST...")
                conn.execute(text("""
                    UPDATE gaming_sessions 
                    SET timestamp_cst = timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago'
                """))
                
                # Check if old timestamp column exists before dropping
                if column_exists(conn, 'gaming_sessions', 'timestamp'):
                    # Drop old column
                    logger.info("Dropping old timestamp column...")
                    conn.execute(text("""
                        ALTER TABLE gaming_sessions 
                        DROP COLUMN timestamp
                    """))
                else:
                    logger.info("Old timestamp column already dropped, skipping...")
                
                # Rename new column if it hasn't been renamed yet
                if column_exists(conn, 'gaming_sessions', 'timestamp_cst'):
                    logger.info("Renaming timestamp_cst to timestamp...")
                    conn.execute(text("""
                        ALTER TABLE gaming_sessions 
                        RENAME COLUMN timestamp_cst TO timestamp
                    """))
                else:
                    logger.info("Column already renamed to timestamp, skipping...")
                
                logger.info("Timestamp migration completed successfully!")
                
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        migrate_timestamps()
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        exit(1) 