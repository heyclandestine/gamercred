import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Game, UserStats, GamingSession, LeaderboardHistory, LeaderboardType, LeaderboardPeriod, Bonus

# Load environment variables
load_dotenv()

def migrate_to_sqlite():
    # Get database URLs
    postgres_url = os.getenv('DATABASE_URL')
    sqlite_url = os.getenv('LOCAL_DATABASE_URL')

    if not postgres_url or not sqlite_url:
        raise ValueError("Both DATABASE_URL and LOCAL_DATABASE_URL must be set")

    print("Connecting to databases...")
    print(f"PostgreSQL URL: {postgres_url}")
    print(f"SQLite URL: {sqlite_url}")
    
    # Create engines
    postgres_engine = create_engine(postgres_url)
    sqlite_engine = create_engine(sqlite_url, connect_args={'check_same_thread': False})

    # Create sessions
    PostgresSession = sessionmaker(bind=postgres_engine)
    SQLiteSession = sessionmaker(bind=sqlite_engine)

    # Create tables in SQLite
    Base.metadata.create_all(sqlite_engine)

    # Clear existing data in SQLite
    print("Clearing existing data in SQLite...")
    with SQLiteSession() as sqlite_session:
        # Drop all tables and recreate them
        Base.metadata.drop_all(sqlite_engine)
        Base.metadata.create_all(sqlite_engine)
        sqlite_session.commit()

    # Start migration
    print("Starting migration...")
    
    with PostgresSession() as postgres_session, SQLiteSession() as sqlite_session:
        # First, migrate Games (no dependencies)
        print("Migrating games...")
        games = postgres_session.query(Game).all()
        print(f"Found {len(games)} games in PostgreSQL")
        for game in games:
            sqlite_session.add(Game(
                id=game.id,
                name=game.name,
                credits_per_hour=game.credits_per_hour,
                backloggd_url=game.backloggd_url,
                rawg_id=game.rawg_id,
                box_art_url=game.box_art_url
            ))
        sqlite_session.commit()
        print(f"Migrated {len(games)} games to SQLite")

        # Second, migrate UserStats (needed for foreign keys)
        print("Migrating user stats...")
        user_stats = postgres_session.query(UserStats).all()
        print(f"Found {len(user_stats)} user stats in PostgreSQL")
        for stat in user_stats:
            sqlite_session.add(UserStats(
                user_id=stat.user_id,
                total_credits=stat.total_credits,
                username=stat.username,
                avatar_url=stat.avatar_url
            ))
        sqlite_session.commit()
        print(f"Migrated {len(user_stats)} user stats to SQLite")

        # Third, migrate LeaderboardPeriods (needed for leaderboard history)
        print("Migrating leaderboard periods...")
        periods = postgres_session.query(LeaderboardPeriod).all()
        print(f"Found {len(periods)} leaderboard periods in PostgreSQL")
        for period in periods:
            sqlite_session.add(LeaderboardPeriod(
                id=period.id,
                leaderboard_type=period.leaderboard_type,
                start_time=period.start_time,
                end_time=period.end_time
            ))
        sqlite_session.commit()
        print(f"Migrated {len(periods)} leaderboard periods to SQLite")

        # Fourth, migrate GamingSessions (depends on users and games)
        print("Migrating gaming sessions...")
        sessions = postgres_session.query(GamingSession).all()
        print(f"Found {len(sessions)} gaming sessions in PostgreSQL")
        for session in sessions:
            sqlite_session.add(GamingSession(
                id=session.id,
                user_id=session.user_id,
                game_id=session.game_id,
                hours=session.hours,
                credits_earned=session.credits_earned,
                timestamp=session.timestamp
            ))
        sqlite_session.commit()
        print(f"Migrated {len(sessions)} gaming sessions to SQLite")

        # Fifth, migrate LeaderboardHistory (depends on users and periods)
        print("Migrating leaderboard history...")
        history = postgres_session.query(LeaderboardHistory).all()
        print(f"Found {len(history)} leaderboard history entries in PostgreSQL")
        for entry in history:
            sqlite_session.add(LeaderboardHistory(
                id=entry.id,
                period_id=entry.period_id,
                user_id=entry.user_id,
                placement=entry.placement,
                credits=entry.credits,
                games_played=entry.games_played,
                most_played_game=entry.most_played_game,
                most_played_hours=entry.most_played_hours,
                leaderboard_type=entry.leaderboard_type
            ))
        sqlite_session.commit()
        print(f"Migrated {len(history)} leaderboard history entries to SQLite")

        # Finally, migrate Bonuses (depends on users)
        print("Migrating bonuses...")
        bonuses = postgres_session.query(Bonus).all()
        print(f"Found {len(bonuses)} bonus entries in PostgreSQL")
        for bonus in bonuses:
            sqlite_session.add(Bonus(
                id=bonus.id,
                user_id=bonus.user_id,
                credits=bonus.credits,
                reason=bonus.reason,
                granted_by=bonus.granted_by,
                timestamp=bonus.timestamp
            ))
        sqlite_session.commit()
        print(f"Migrated {len(bonuses)} bonus entries to SQLite")

    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_to_sqlite() 