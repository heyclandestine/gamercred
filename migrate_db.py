from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

def migrate_db():
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment variables
    database_url = os.getenv('DATABASE_URL') or os.getenv('LOCAL_DATABASE_URL')
    if not database_url:
        raise ValueError("No database URL found. Set DATABASE_URL or LOCAL_DATABASE_URL environment variable")
    
    print(f"Connecting to database: {database_url}")
    
    # Create the database engine
    engine = create_engine(database_url)
    
    # Check if backloggd_url column exists
    with engine.connect() as conn:
        # Get table info
        result = conn.execute(text("PRAGMA table_info(games)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'backloggd_url' not in columns:
            print("Adding backloggd_url column to games table...")
            conn.execute(text("ALTER TABLE games ADD COLUMN backloggd_url TEXT"))
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("backloggd_url column already exists.")

if __name__ == '__main__':
    migrate_db() 