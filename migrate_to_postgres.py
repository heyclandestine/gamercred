import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from models import Base, LeaderboardPeriod, LeaderboardHistory, GamingSession, Game, Bonus, UserStats
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

def migrate_data():
    try:
        # Get database URLs
        postgres_url = os.getenv('DATABASE_URL')
        sqlite_url = 'sqlite:///gamer_cred.db'

        print(f"PostgreSQL URL: {postgres_url}")
        print(f"SQLite URL: {sqlite_url}")

        # Create engines
        postgres_engine = create_engine(postgres_url)
        sqlite_engine = create_engine(sqlite_url)

        # Inspect SQLite database
        print("\nInspecting SQLite database structure:")
        inspector = inspect(sqlite_engine)
        tables = inspector.get_table_names()
        print(f"Found tables: {tables}")
        
        for table in tables:
            columns = inspector.get_columns(table)
            print(f"\nTable '{table}' columns:")
            for column in columns:
                print(f"  - {column['name']}: {column['type']}")

        # Create sessions
        PostgresSession = sessionmaker(bind=postgres_engine)
        SQLiteSession = sessionmaker(bind=sqlite_engine)

        postgres_session = PostgresSession()
        sqlite_session = SQLiteSession()

        try:
            # Drop all existing tables in PostgreSQL
            print("\nDropping existing tables in PostgreSQL...")
            Base.metadata.drop_all(postgres_engine)
            print("Tables dropped successfully")

            # Create tables in PostgreSQL
            print("\nCreating tables in PostgreSQL...")
            Base.metadata.create_all(postgres_engine)
            print("Tables created successfully")

            # Migrate UserStats first (since other tables depend on it)
            print("\nMigrating user stats...")
            user_stats = sqlite_session.query(UserStats).all()
            for stat in user_stats:
                new_stat = UserStats(
                    id=stat.id,
                    user_id=stat.user_id,
                    total_credits=stat.total_credits,
                    username=stat.username,
                    avatar_url=stat.avatar_url
                )
                postgres_session.add(new_stat)
            postgres_session.commit()
            print(f"Migrated {len(user_stats)} user stats")

            # Migrate Games
            print("\nMigrating games...")
            games = sqlite_session.query(Game).all()
            for game in games:
                new_game = Game(
                    id=game.id,
                    name=game.name,
                    credits_per_hour=game.credits_per_hour,
                    added_by=game.added_by,
                    backloggd_url=game.backloggd_url,
                    rawg_id=game.rawg_id,
                    box_art_url=game.box_art_url
                )
                postgres_session.add(new_game)
            postgres_session.commit()
            print(f"Migrated {len(games)} games")

            # Migrate LeaderboardPeriods
            print("\nMigrating leaderboard periods...")
            periods = sqlite_session.query(LeaderboardPeriod).all()
            for period in periods:
                new_period = LeaderboardPeriod(
                    id=period.id,
                    leaderboard_type=period.leaderboard_type,
                    start_time=period.start_time,
                    end_time=period.end_time,
                    is_active=period.is_active
                )
                postgres_session.add(new_period)
            postgres_session.commit()
            print(f"Migrated {len(periods)} leaderboard periods")

            # Migrate LeaderboardHistory
            print("\nMigrating leaderboard history...")
            entries = sqlite_session.query(LeaderboardHistory).all()
            for entry in entries:
                new_entry = LeaderboardHistory(
                    id=entry.id,
                    user_id=entry.user_id,
                    period_id=entry.period_id,
                    leaderboard_type=entry.leaderboard_type,
                    placement=entry.placement,
                    credits=entry.credits,
                    games_played=entry.games_played,
                    most_played_game=entry.most_played_game,
                    most_played_hours=entry.most_played_hours,
                    timestamp=entry.timestamp
                )
                postgres_session.add(new_entry)
            postgres_session.commit()
            print(f"Migrated {len(entries)} leaderboard entries")

            # Migrate GamingSessions
            print("\nMigrating gaming sessions...")
            sessions = sqlite_session.query(GamingSession).all()
            for session in sessions:
                new_session = GamingSession(
                    user_id=session.user_id,
                    game_id=session.game_id,
                    hours=session.hours,
                    credits_earned=session.credits_earned,
                    timestamp=session.timestamp
                )
                postgres_session.add(new_session)
            postgres_session.commit()
            print(f"Migrated {len(sessions)} gaming sessions")

            # Migrate Bonuses
            print("\nMigrating bonuses...")
            bonuses = sqlite_session.query(Bonus).all()
            for bonus in bonuses:
                new_bonus = Bonus(
                    id=bonus.id,
                    user_id=bonus.user_id,
                    credits=bonus.credits,
                    reason=bonus.reason,
                    granted_by=bonus.granted_by,
                    timestamp=bonus.timestamp
                )
                postgres_session.add(new_bonus)
            postgres_session.commit()
            print(f"Migrated {len(bonuses)} bonuses")

            print("\nMigration completed successfully!")

        except Exception as e:
            print(f"Error during migration: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            postgres_session.rollback()
            raise

        finally:
            postgres_session.close()
            sqlite_session.close()

    except Exception as e:
        print(f"Error setting up migration: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate_data() 