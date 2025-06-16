import asyncio
from storage import GameStorage, get_period_boundaries
from models import LeaderboardPeriod
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://gamercred_user:O03x7e1c4ghsHBTUFWt56apJvDYHQp8G@dpg-d10bga6mcj7s73c4m31g-a.virginia-postgres.render.com/gamercred')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

async def fix_single_period(period_id):
    storage = GameStorage()
    session = Session()
    try:
        period = session.query(LeaderboardPeriod).filter(LeaderboardPeriod.id == period_id).first()
        if not period:
            print(f"No period found with id {period_id}")
            return
        print(f"Fixing period {period.id}: {period.start_time} to {period.end_time}")
        # Use unified period boundary calculation
        period_type = period.leaderboard_type.value.lower()
        start, end = get_period_boundaries(period.start_time, period_type)
        leaderboard_data = await storage.get_leaderboard_by_timeframe(
            period.leaderboard_type, custom_start=start, custom_end=end
        )
        # Temporarily allow updating this period
        was_active = period.is_active
        period.is_active = True
        session.commit()
        await storage.record_leaderboard_placements(period.leaderboard_type, leaderboard_data, period)
        period.is_active = was_active
        session.commit()
        print(f"Updated leaderboard history for period {period_id}")
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_single_leaderboard_period.py <period_id>")
        sys.exit(1)
    period_id = int(sys.argv[1])
    asyncio.run(fix_single_period(period_id)) 