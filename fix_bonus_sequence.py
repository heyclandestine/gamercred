import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variables
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

print(f"Using database URL: {DATABASE_URL[:50]}...")

def fix_bonus_sequence():
    """Fix the PostgreSQL sequence for the bonuses table"""
    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            print("Connected to database successfully!")
            
            # Start a transaction
            with conn.begin():
                print("Started transaction...")
                
                # Get the current maximum ID from the bonuses table
                result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM bonuses"))
                max_id = result.scalar()
                print(f"Current maximum ID in bonuses table: {max_id}")
                
                # Get the current sequence value
                result = conn.execute(text("SELECT last_value FROM bonuses_id_seq"))
                current_seq = result.scalar()
                print(f"Current sequence value: {current_seq}")
                
                # If the sequence is behind the max ID, reset it
                if current_seq <= max_id:
                    new_seq = max_id + 1
                    print(f"Resetting sequence to {new_seq}")
                    conn.execute(text(f"ALTER SEQUENCE bonuses_id_seq RESTART WITH {new_seq}"))
                    print("Sequence reset successfully!")
                else:
                    print("Sequence is already correct.")
                
                # Verify the fix
                result = conn.execute(text("SELECT nextval('bonuses_id_seq')"))
                next_val = result.scalar()
                print(f"Next sequence value will be: {next_val}")
                
                # Rollback the test value
                conn.execute(text("SELECT setval('bonuses_id_seq', :val, false)"), {"val": new_seq - 1})
                print("Test value rolled back.")
                
    except Exception as e:
        print(f"Error fixing bonus sequence: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        engine.dispose()
        print("Database connection closed.")

if __name__ == "__main__":
    print("Starting bonus sequence fix...")
    fix_bonus_sequence()
    print("Bonus sequence fix completed!") 