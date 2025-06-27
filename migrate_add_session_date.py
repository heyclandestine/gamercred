import os
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL environment variable is not set')

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

# 1. Add session_date column if not exists
cur.execute("""
SELECT 1 FROM information_schema.columns WHERE table_name='gaming_sessions' AND column_name='session_date'
""")
if not cur.fetchone():
    print('Adding session_date column...')
    cur.execute("""
        ALTER TABLE gaming_sessions
        ADD COLUMN session_date date GENERATED ALWAYS AS (timestamp::date) STORED
    """)
else:
    print('session_date column already exists.')

# 2. Add index if not exists
cur.execute("""
SELECT 1 FROM pg_indexes WHERE tablename='gaming_sessions' AND indexname='idx_gaming_sessions_user_id_session_date'
""")
if not cur.fetchone():
    print('Creating index on (user_id, session_date)...')
    cur.execute("""
        CREATE INDEX idx_gaming_sessions_user_id_session_date
        ON gaming_sessions(user_id, session_date)
    """)
else:
    print('Index already exists.')

# 3. Vacuum/Analyze (optional)
print('Running VACUUM ANALYZE...')
cur.execute('VACUUM ANALYZE gaming_sessions;')

cur.close()
conn.close()
print('Migration complete.') 