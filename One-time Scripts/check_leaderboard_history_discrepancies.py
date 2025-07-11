from models import LeaderboardHistory, LeaderboardPeriod, LeaderboardType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import asyncio
import pytz
import os

# Import your storage logic (adjust import as needed)
from storage import GameStorage, get_period_boundaries

DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

storage = GameStorage()

async def check_discrepancies():
    periods = session.query(LeaderboardPeriod).filter(
        LeaderboardPeriod.leaderboard_type.in_([LeaderboardType.WEEKLY, LeaderboardType.MONTHLY])
    ).all()
    print(f"Found {len(periods)} periods to check.")
    discrepancies = []
    for period in periods:
        print(f"Checking period {period.id} ({period.leaderboard_type}) {period.start_time} - {period.end_time}")
        # Use unified period boundary calculation
        period_type = period.leaderboard_type.value.lower()
        start, end = get_period_boundaries(period.start_time, period_type)
        # Recalculate leaderboard for this period using unified boundaries
        recalculated = await storage.get_leaderboard_by_timeframe(period.leaderboard_type, period=None, custom_start=start, custom_end=end)
        recalculated_dict = {int(user_id): (credits, games, most_played, most_played_hours, total_hours)
                             for user_id, credits, games, most_played, most_played_hours, total_hours in recalculated}
        stored = session.query(LeaderboardHistory).filter(LeaderboardHistory.period_id == period.id).all()
        for entry in stored:
            recalc = recalculated_dict.get(entry.user_id)
            if not recalc:
                discrepancies.append((period.id, entry.user_id, 'Missing in recalculated leaderboard'))
                print(f"User {entry.user_id} in period {period.id} is missing in recalculated leaderboard.")
                continue
            fields = ['credits', 'games_played', 'most_played_game', 'most_played_hours', 'total_hours']
            stored_values = [entry.credits, entry.games_played, entry.most_played_game, entry.most_played_hours, getattr(entry, 'total_hours', None)]
            for i, field in enumerate(fields):
                recalc_value = recalc[i]
                stored_value = stored_values[i]
                if isinstance(recalc_value, float) and isinstance(stored_value, float):
                    if abs(recalc_value - stored_value) > 0.01:
                        discrepancies.append((period.id, entry.user_id, field, stored_value, recalc_value))
                        print(f"Discrepancy for user {entry.user_id} in period {period.id} field {field}: stored={stored_value}, recalculated={recalc_value}")
                else:
                    if recalc_value != stored_value:
                        discrepancies.append((period.id, entry.user_id, field, stored_value, recalc_value))
                        print(f"Discrepancy for user {entry.user_id} in period {period.id} field {field}: stored={stored_value}, recalculated={recalc_value}")
    print(f"\nTotal discrepancies found: {len(discrepancies)}")
    if discrepancies:
        print("Summary of discrepancies:")
        for d in discrepancies:
            print(d)
    else:
        print("No discrepancies found!")

if __name__ == "__main__":
    asyncio.run(check_discrepancies()) 