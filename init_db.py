from sqlalchemy import create_engine
from models import Base
import os

def init_db():
    # Get the absolute path to the database file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'gamer_cred.db')
    
    print(f"Creating database at: {db_path}")
    
    # Create the database engine
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db() 