import sqlite3

def update_names(db_path):
    con = sqlite3.connect(db_path)
    users = dict(con.execute('SELECT user_id, name FROM user_stats'))
    tables = ['gaming_sessions', 'leaderboard_history', 'bonuses']
    for table in tables:
        rows = con.execute(f'SELECT rowid, user_id FROM {table}').fetchall()
        for rowid, user_id in rows:
            name = users.get(user_id)
            if name:
                con.execute(f'UPDATE {table} SET name=? WHERE rowid=?', (name, rowid))
        con.commit()
    con.close()

if __name__ == '__main__':
    update_names('gamer_cred.db') 