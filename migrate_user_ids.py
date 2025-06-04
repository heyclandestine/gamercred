import sqlite3
import os

def migrate_user_ids(db_path):
    """Migrate user_id columns from BigInteger to String in all tables"""
    print(f"Starting migration of user IDs in {db_path}")
    
    # Connect to the database
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    try:
        # Drop all views first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view';")
        views = cursor.fetchall()
        for (view_name,) in views:
            print(f"Dropping view: {view_name}")
            cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
        
        # Clean up any leftover temporary tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_temp';")
        temp_tables = cursor.fetchall()
        for (table_name,) in temp_tables:
            print(f"Dropping leftover temporary table: {table_name}")
            cursor.execute(f"DROP TABLE {table_name}")
        
        # Get list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            # Check if table has user_id column
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            has_user_id = any(col[1] == 'user_id' for col in columns)
            
            if has_user_id:
                print(f"Migrating {table_name}...")
                
                # Get all column definitions
                column_defs = []
                for col in columns:
                    if col[1] == 'user_id':
                        # Change user_id to TEXT
                        column_defs.append(f"{col[1]} TEXT")
                    else:
                        # Keep other columns as is
                        column_defs.append(f"{col[1]} {col[2]}")
                
                # Create temporary table with string user_id
                create_table_sql = f"""
                    CREATE TABLE {table_name}_temp (
                        {', '.join(column_defs)}
                    )
                """
                print(f"Creating temp table with SQL: {create_table_sql}")
                cursor.execute(create_table_sql)
                
                # Copy data with user_id converted to string
                cursor.execute(f"""
                    INSERT INTO {table_name}_temp
                    SELECT 
                        {', '.join(f"CAST({col[1]} AS TEXT)" if col[1] == 'user_id' else col[1] for col in columns)}
                    FROM {table_name}
                """)
                
                # Drop original table
                cursor.execute(f"DROP TABLE {table_name}")
                
                # Rename temporary table to original name
                cursor.execute(f"ALTER TABLE {table_name}_temp RENAME TO {table_name}")
                
                print(f"Successfully migrated {table_name}")
        
        # Commit changes
        con.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        con.rollback()
    finally:
        con.close()

if __name__ == "__main__":
    # Get the database path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gamer_cred.db")
    migrate_user_ids(db_path) 