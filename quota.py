# quota.py
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, text

# --- engine bootstrap -------------------------------------------------
_engine = None
def _db_url():
    url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or "sqlite:///app.db"
    # Heroku/Railway style prefix fix
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_db_url(), pool_pre_ping=True)
    return _engine

def _today_utc_str():
    return datetime.now(timezone.utc).date().isoformat()

# --- schema helper (portable: Postgres/SQLite) ------------------------
def _ensure_table():
    eng = get_engine()
    with eng.begin() as conn:
        try:
            # Postgres-friendly
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_plays(
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    game TEXT NOT NULL,
                    day DATE NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(user_id, game, day)
                );
            """))
        except Exception:
            # SQLite fallback (DATE -> TEXT, AUTOINCREMENT)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_plays(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    game TEXT NOT NULL,
                    day TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(user_id, game, day)
                );
            """))

# --- public API -------------------------------------------------------
DEFAULT_LIMIT = int(os.getenv("DAILY_FREE_GAMES", "5"))

def get_quota(user_id: str, game: str, limit: int = DEFAULT_LIMIT):
    """Return {'ok', 'limit', 'used', 'remaining'} for today (UTC)."""
    _ensure_table()
    eng = get_engine()
    day = _today_utc_str()
    with eng.begin() as conn:
        row = conn.execute(
            text("SELECT count FROM daily_plays WHERE user_id=:u AND game=:g AND day=:d"),
            {"u": user_id, "g": game, "d": day},
        ).fetchone()
        used = int(row[0]) if row else 0
    remaining = max(0, limit - used)
    return {"ok": True, "limit": limit, "used": used, "remaining": remaining}

def inc_quota(user_id: str, game: str, limit: int = DEFAULT_LIMIT):
    """Atomically increment today's count; returns same shape as get_quota."""
    _ensure_table()
    eng = get_engine()
    day = _today_utc_str()
    with eng.begin() as conn:
        # Try Postgres upsert first, then SQLite upsert
        try:
            conn.execute(text("""
                INSERT INTO daily_plays (user_id, game, day, count)
                VALUES (:u, :g, :d, 1)
                ON CONFLICT (user_id, game, day)
                DO UPDATE SET count = daily_plays.count + 1;
            """), {"u": user_id, "g": game, "d": day})
        except Exception:
            conn.execute(text("""
                INSERT INTO daily_plays (user_id, game, day, count)
                VALUES (:u, :g, :d, 1)
                ON CONFLICT(user_id, game, day)
                DO UPDATE SET count = count + 1;
            """), {"u": user_id, "g": game, "d": day})
    return get_quota(user_id, game, limit)