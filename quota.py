from datetime import datetime, timezone
from sqlalchemy import text

DAILY_LIMIT = 5

def _utc_today():
    return datetime.now(timezone.utc).date()

def get_quota(db, user_id, game_key):
    day = _utc_today()
    row = db.session.execute(
        text("SELECT used FROM daily_plays WHERE user_id=:u AND game_key=:g AND day_utc=:d"),
        {"u": user_id, "g": game_key, "d": day},
    ).fetchone()
    used = (row[0] if row else 0)
    return {"used": used, "limit": DAILY_LIMIT, "left": max(0, DAILY_LIMIT - used)}

def inc_quota(db, user_id, game_key):
    day = _utc_today()
    db.session.execute(text("""
      INSERT INTO daily_plays (user_id, game_key, day_utc, used)
      VALUES (:u,:g,:d,1)
      ON CONFLICT (user_id, game_key, day_utc)
      DO UPDATE SET used = LEAST(daily_plays.used + 1, :lim)
    """), {"u": user_id, "g": game_key, "d": day, "lim": DAILY_LIMIT})
    db.session.commit()