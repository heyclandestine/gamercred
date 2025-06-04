print("Script started!")
import sqlite3
import os
from sqlalchemy import create_engine, Table, MetaData, Column, Integer, String, inspect, text

# Define the database path - make sure this matches the path in your backend/app.py
DATABASE_PATH = 'C:/Users/kende/Downloads/DiscordCompanion/gamer_cred.db'

def add_columns_if_not_exists():
    """Adds rawg_id and box_art_url columns to the games table if they don't exist."""
    engine = None
    try:
        # Create engine
        engine = create_engine(f'sqlite:///{DATABASE_PATH}')

        # Check if the database file exists
        if not os.path.exists(DATABASE_PATH):
            print(f"Error: Database file not found at {DATABASE_PATH}")
            print("Please ensure the database file exists before running this script.")
            return

        # Use reflection to get table information
        metadata = MetaData()
        metadata.reflect(bind=engine)

        # Check if 'games' table exists
        if 'games' not in metadata.tables:
            print("Error: 'games' table not found in the database.")
            print("Please ensure your database is initialized correctly.")
            return

        games_table = metadata.tables['games']
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('games')]

        columns_to_add = []
        if 'rawg_id' not in columns:
            columns_to_add.append(Column('rawg_id', Integer, nullable=True))
            print("Column 'rawg_id' not found. Preparing to add.")
        else:
            print("Column 'rawg_id' already exists.")

        if 'box_art_url' not in columns:
            columns_to_add.append(Column('box_art_url', String, nullable=True))
            print("Column 'box_art_url' not found. Preparing to add.")
        else:
            print("Column 'box_art_url' already exists.")

        if not columns_to_add:
            print("All required columns already exist. No migration needed.")
            return

        # Use a raw connection to execute ALTER TABLE statements
        # SQLAlchemy's ORM doesn't handle simple ALTER TABLE ADD COLUMN well for SQLite
        with engine.connect() as connection:
            for col in columns_to_add:
                col_type = "INTEGER" if isinstance(col.type, Integer) else "VARCHAR"
                alter_sql = f"ALTER TABLE games ADD COLUMN {col.name} {col_type} NULL"
                print(f"Executing: {alter_sql}")
                connection.execute(text(alter_sql))
            connection.execute(text("COMMIT")) # Wrap the COMMIT statement with text()
            print("Successfully added missing columns to 'games' table.")

    except Exception as e:
        print(f"An error occurred during migration: {e}")
    finally:
        if engine:
            engine.dispose()

if __name__ == "__main__":
    add_columns_if_not_exists()