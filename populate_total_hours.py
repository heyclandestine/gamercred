from models import LeaderboardHistory, GamingSession
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import pytz
from storage import get_period_boundaries

DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    histories = session.query(LeaderboardHistory).all()
    print(f"Found {len(histories)} leaderboard history entries.")

    for history in histories:
        # Use unified period boundary calculation
        period_type = history.period.leaderboard_type.value.lower()
        start, end = get_period_boundaries(history.period.start_time, period_type)
        total_hours = session.query(func.sum(GamingSession.hours)).filter(
            GamingSession.user_id == history.user_id,
            GamingSession.timestamp >= start,
            GamingSession.timestamp < end
        ).scalar() or 0.0
        history.total_hours = float(total_hours)
        print(f"Updated user {history.user_id} period {history.period_id}: total_hours={total_hours}")

    session.commit()
    print("All leaderboard history entries updated with total_hours.")
finally:
    session.close()