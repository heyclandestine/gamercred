import sqlite3

def migrate():
    conn = sqlite3.connect('gaming_credits.db')
    cursor = conn.cursor()
    
    try:
        # Add background_video_url column
        cursor.execute('ALTER TABLE user_preferences ADD COLUMN background_video_url TEXT')
        print("✓ Added background_video_url column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("✓ background_video_url column already exists")
        else:
            raise
    
    try:
        # Add background_type column
        cursor.execute('ALTER TABLE user_preferences ADD COLUMN background_type TEXT DEFAULT "image"')
        print("✓ Added background_type column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("✓ background_type column already exists")
        else:
            raise
    
    conn.commit()
    conn.close()
    print("✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate() 