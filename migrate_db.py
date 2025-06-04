import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from models import Base, Game, UserStats, GamingSession, LeaderboardHistory, LeaderboardType, LeaderboardPeriod, Bonus

    # Load environment variables
    load_dotenv()
    
def migrate_data():
    # Get database URLs
    postgres_url = os.getenv('DATABASE_URL')
    sqlite_path = 'gamer_cred.db'  # Use the local SQLite database directly

    if not postgres_url:
        raise ValueError("DATABASE_URL must be set")

    print("Connecting to databases...")
    print(f"PostgreSQL URL: {postgres_url}")
    print(f"SQLite path: {sqlite_path}")
    
    # Create engines
    sqlite_engine = create_engine(f'sqlite:///{sqlite_path}', connect_args={'check_same_thread': False})
    postgres_engine = create_engine(postgres_url)

    # Create sessions
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)

    # Create tables in PostgreSQL
    Base.metadata.create_all(postgres_engine)

    # Clear existing data in PostgreSQL
    print("Clearing existing data in PostgreSQL...")
    with PostgresSession() as postgres_session:
        # Drop all tables and recreate them
        Base.metadata.drop_all(postgres_engine)
        Base.metadata.create_all(postgres_engine)
        
        # Reset all sequences
        print("Resetting sequences...")
        postgres_session.execute(text("ALTER SEQUENCE games_id_seq RESTART WITH 1"))
        postgres_session.execute(text("ALTER SEQUENCE user_stats_id_seq RESTART WITH 1"))
        postgres_session.execute(text("ALTER SEQUENCE gaming_sessions_id_seq RESTART WITH 1"))
        postgres_session.execute(text("ALTER SEQUENCE leaderboard_periods_id_seq RESTART WITH 1"))
        postgres_session.execute(text("ALTER SEQUENCE leaderboard_history_id_seq RESTART WITH 1"))
        postgres_session.execute(text("ALTER SEQUENCE bonuses_id_seq RESTART WITH 1"))
        postgres_session.commit()

    # Start migration
    print("Starting migration...")
    
    with SQLiteSession() as sqlite_session, PostgresSession() as postgres_session:
        # First, migrate Games (no dependencies)
        print("Migrating games...")
        games = sqlite_session.query(Game).all()
        print(f"Found {len(games)} games in SQLite")
        for game in games:
            # Use upsert for games
            stmt = text("""
                INSERT INTO games (id, name, credits_per_hour, backloggd_url, rawg_id, box_art_url)
                VALUES (:id, :name, :credits_per_hour, :backloggd_url, :rawg_id, :box_art_url)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    credits_per_hour = EXCLUDED.credits_per_hour,
                    backloggd_url = EXCLUDED.backloggd_url,
                    rawg_id = EXCLUDED.rawg_id,
                    box_art_url = EXCLUDED.box_art_url
            """)
            postgres_session.execute(stmt, {
                'id': game.id,
                'name': game.name,
                'credits_per_hour': game.credits_per_hour,
                'backloggd_url': game.backloggd_url,
                'rawg_id': game.rawg_id,
                'box_art_url': game.box_art_url
            })
        postgres_session.commit()
        print(f"Migrated {len(games)} games to PostgreSQL")

        # Second, migrate UserStats (needed for foreign keys)
        print("Migrating user stats...")
        user_stats = sqlite_session.query(UserStats).all()
        print(f"Found {len(user_stats)} user stats in SQLite")
        for stat in user_stats:
            # Use upsert for user stats
            stmt = text("""
                INSERT INTO user_stats (user_id, total_credits, username, avatar_url)
                VALUES (:user_id, :total_credits, :username, :avatar_url)
                ON CONFLICT (user_id) DO UPDATE SET
                    total_credits = EXCLUDED.total_credits,
                    username = EXCLUDED.username,
                    avatar_url = EXCLUDED.avatar_url
            """)
            postgres_session.execute(stmt, {
                'user_id': stat.user_id,
                'total_credits': stat.total_credits,
                'username': stat.username,
                'avatar_url': stat.avatar_url
            })
        postgres_session.commit()
        print(f"Migrated {len(user_stats)} user stats to PostgreSQL")

        # Third, migrate LeaderboardPeriods
        print("Migrating leaderboard periods...")
        periods = sqlite_session.query(LeaderboardPeriod).all()
        print(f"Found {len(periods)} leaderboard periods in SQLite")
        for period in periods:
            # Use upsert for periods
            stmt = text("""
                INSERT INTO leaderboard_periods (id, leaderboard_type, start_time, end_time)
                VALUES (:id, :leaderboard_type, :start_time, :end_time)
                ON CONFLICT (id) DO UPDATE SET
                    leaderboard_type = EXCLUDED.leaderboard_type,
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time
            """)
            postgres_session.execute(stmt, {
                'id': period.id,
                'leaderboard_type': period.leaderboard_type.name,  # Use enum name (WEEKLY/MONTHLY) instead of value
                'start_time': period.start_time,
                'end_time': period.end_time
            })
        postgres_session.commit()
        print(f"Migrated {len(periods)} leaderboard periods to PostgreSQL")

        # Fourth, migrate GamingSessions
        print("Migrating gaming sessions...")
        sessions = sqlite_session.query(GamingSession).all()
        print(f"Found {len(sessions)} gaming sessions in SQLite")
        for session in sessions:
            # Use upsert for gaming sessions
            stmt = text("""
                INSERT INTO gaming_sessions (id, user_id, game_id, hours, credits_earned, timestamp)
                VALUES (:id, :user_id, :game_id, :hours, :credits_earned, :timestamp)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    game_id = EXCLUDED.game_id,
                    hours = EXCLUDED.hours,
                    credits_earned = EXCLUDED.credits_earned,
                    timestamp = EXCLUDED.timestamp
            """)
            postgres_session.execute(stmt, {
                'id': session.id,
                'user_id': session.user_id,
                'game_id': session.game_id,
                'hours': session.hours,
                'credits_earned': session.credits_earned,
                'timestamp': session.timestamp
            })
        postgres_session.commit()
        print(f"Migrated {len(sessions)} gaming sessions to PostgreSQL")

        # Fifth, migrate LeaderboardHistory
        print("Migrating leaderboard history...")
        history = sqlite_session.query(LeaderboardHistory).all()
        print(f"Found {len(history)} leaderboard history entries in SQLite")
        for entry in history:
            # Use upsert for leaderboard history
            stmt = text("""
                INSERT INTO leaderboard_history (id, period_id, user_id, placement, credits, games_played, 
                    most_played_game, most_played_hours, leaderboard_type)
                VALUES (:id, :period_id, :user_id, :placement, :credits, :games_played, 
                    :most_played_game, :most_played_hours, :leaderboard_type)
                ON CONFLICT (id) DO UPDATE SET
                    period_id = EXCLUDED.period_id,
                    user_id = EXCLUDED.user_id,
                    placement = EXCLUDED.placement,
                    credits = EXCLUDED.credits,
                    games_played = EXCLUDED.games_played,
                    most_played_game = EXCLUDED.most_played_game,
                    most_played_hours = EXCLUDED.most_played_hours,
                    leaderboard_type = EXCLUDED.leaderboard_type
            """)
            postgres_session.execute(stmt, {
                'id': entry.id,
                'period_id': entry.period_id,
                'user_id': entry.user_id,
                'placement': entry.placement,
                'credits': entry.credits,
                'games_played': entry.games_played,
                'most_played_game': entry.most_played_game,
                'most_played_hours': entry.most_played_hours,
                'leaderboard_type': entry.leaderboard_type.name  # Use enum name (WEEKLY/MONTHLY) instead of value
            })
        postgres_session.commit()
        print(f"Migrated {len(history)} leaderboard history entries to PostgreSQL")

        # Finally, migrate Bonuses
        print("Migrating bonuses...")
        bonuses = sqlite_session.query(Bonus).all()
        print(f"Found {len(bonuses)} bonus entries in SQLite")
        for bonus in bonuses:
            # Use upsert for bonuses
            stmt = text("""
                INSERT INTO bonuses (id, user_id, credits, reason, granted_by, timestamp)
                VALUES (:id, :user_id, :credits, :reason, :granted_by, :timestamp)
                ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    credits = EXCLUDED.credits,
                    reason = EXCLUDED.reason,
                    granted_by = EXCLUDED.granted_by,
                    timestamp = EXCLUDED.timestamp
            """)
            postgres_session.execute(stmt, {
                'id': bonus.id,
                'user_id': bonus.user_id,
                'credits': bonus.credits,
                'reason': bonus.reason,
                'granted_by': bonus.granted_by,
                'timestamp': bonus.timestamp
            })
        postgres_session.commit()
        print(f"Migrated {len(bonuses)} bonus entries to PostgreSQL")

            print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_data() 