import os, sqlite3, secrets
from pathlib import Path
from flask import Blueprint, g, render_template, request, jsonify, session, redirect, url_for
from blueprints.credits import spend_credits, _get_user_id
from models import db, User

arcade_bp = Blueprint('arcade', __name__, url_prefix='/game')

# Database setup for arcade games
APP_DIR = Path(__file__).resolve().parent.parent
ARCADE_DB_PATH = APP_DIR / "arcade.db"
CREDITS_PER_EXTRA_PLAY = 5  # after 5 free plays per game

def get_arcade_db():
    """Get arcade database connection"""
    if "arcade_db" not in g:
        g.arcade_db = sqlite3.connect(ARCADE_DB_PATH)
        g.arcade_db.row_factory = sqlite3.Row
        g.arcade_db.execute("PRAGMA foreign_keys=ON;")
    return g.arcade_db

@arcade_bp.teardown_app_request
def close_arcade_db(error):
    """Close arcade database connection"""
    db = g.pop("arcade_db", None)
    if db is not None:
        db.close()

def init_arcade_db():
    """Initialize arcade database with schema"""
    db = sqlite3.connect(ARCADE_DB_PATH)
    db.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA foreign_keys=ON;

    -- Per-game profile (5 free plays per game)
    CREATE TABLE IF NOT EXISTS game_profile (
      user_id INTEGER NOT NULL,
      game_code TEXT NOT NULL,                 -- 'ttt' or 'c4'
      plays INTEGER NOT NULL DEFAULT 0,
      wins  INTEGER NOT NULL DEFAULT 0,
      free_remaining INTEGER NOT NULL DEFAULT 5,
      last_play_at TEXT,
      PRIMARY KEY (user_id, game_code)
    );

    CREATE INDEX IF NOT EXISTS idx_gp_wins ON game_profile (game_code, wins DESC);
    """)
    db.commit()
    db.close()

# Initialize database when blueprint is imported
init_arcade_db()

def ensure_profile(user_id: int, game: str):
    """Ensure user has a game profile"""
    db = get_arcade_db()
    db.execute("""
        INSERT OR IGNORE INTO game_profile (user_id, game_code)
        VALUES (?, ?)
    """, (user_id, game))
    db.commit()

def badge_for_wins(w: int) -> str:
    """Get badge for win count"""
    if w >= 100: return "🏆"
    if w >= 50:  return "🥇"
    if w >= 25:  return "🥈"
    if w >= 10:  return "🥉"
    return "•"

# Routes
@arcade_bp.route("/tictactoe")
def tictactoe():
    """Tic-Tac-Toe game page"""
    return render_template("arcade/tictactoe.html")

@arcade_bp.route("/connect4")
def connect4():
    """Connect 4 game page"""
    return render_template("arcade/connect4.html")

# API endpoints
@arcade_bp.route("/api/start", methods=["POST"])
def api_game_start():
    """Start a game round - uses free play or charges credits"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"ok": False, "error": "not_logged_in"}), 401

    data = request.get_json(silent=True) or {}
    game = (data.get("game") or "").strip().lower()
    if game not in ("ttt", "c4"):
        return jsonify({"ok": False, "error": "invalid_game"}), 400

    ensure_profile(user_id, game)
    db = get_arcade_db()

    # Get current free plays remaining
    row = db.execute(
        "SELECT free_remaining FROM game_profile WHERE user_id=? AND game_code=?",
        (user_id, game)
    ).fetchone()
    free_remaining = int(row["free_remaining"]) if row else 0

    charged = 0
    try:
        if free_remaining > 0:
            # Use free play
            free_remaining -= 1
            db.execute("""
                UPDATE game_profile
                   SET free_remaining=?, last_play_at=datetime('now')
                 WHERE user_id=? AND game_code=?
            """, (free_remaining, user_id, game))
            db.commit()
        else:
            # Charge credits using existing credits system
            try:
                spend_credits(user_id, CREDITS_PER_EXTRA_PLAY, f"{game}_play")
                charged = CREDITS_PER_EXTRA_PLAY
            except ValueError as e:
                if "INSUFFICIENT_CREDITS" in str(e):
                    # Get current credits
                    user = User.query.get(user_id)
                    credits = user.mini_word_credits if user else 0
                    return jsonify({"ok": False, "error": "insufficient_credits", "credits": credits}), 400
                raise

        # Get updated info
        user = User.query.get(user_id)
        credits = user.mini_word_credits if user else 0

        row = db.execute(
            "SELECT free_remaining FROM game_profile WHERE user_id=? AND game_code=?",
            (user_id, game)
        ).fetchone()
        free_remaining = int(row["free_remaining"]) if row else 0

        return jsonify({
            "ok": True,
            "free_remaining": free_remaining,
            "charged": charged,
            "credits": credits
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@arcade_bp.route("/api/result", methods=["POST"])
def api_game_result():
    """Record game result"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"ok": False, "error": "not_logged_in"}), 401

    data = request.get_json(silent=True) or {}
    game = (data.get("game") or "").strip().lower()
    won = bool(data.get("won"))

    if game not in ("ttt", "c4"):
        return jsonify({"ok": False, "error": "invalid_game"}), 400

    ensure_profile(user_id, game)
    db = get_arcade_db()

    if won:
        row = db.execute("""
            UPDATE game_profile
               SET plays = plays + 1,
                   wins  = wins  + 1,
                   last_play_at = datetime('now')
             WHERE user_id=? AND game_code=?
         RETURNING plays, wins
        """, (user_id, game)).fetchone()
    else:
        row = db.execute("""
            UPDATE game_profile
               SET plays = plays + 1,
                   last_play_at = datetime('now')
             WHERE user_id=? AND game_code=?
         RETURNING plays, wins
        """, (user_id, game)).fetchone()

    db.commit()
    plays, wins = int(row["plays"]), int(row["wins"])
    return jsonify({"ok": True, "plays": plays, "wins": wins, "badge": badge_for_wins(wins)})

@arcade_bp.route("/api/leaderboard/<game>")
def api_leaderboard(game):
    """Get leaderboard for a game"""
    game = (game or "").lower()
    if game not in ("ttt", "c4"):
        return jsonify({"ok": False, "error": "invalid_game"}), 400

    # Join with main users table
    from models import User
    arcade_db = get_arcade_db()

    # Get all user IDs and game stats from arcade DB
    rows = arcade_db.execute("""
        SELECT user_id, wins, plays
          FROM game_profile
         WHERE game_code=?
      ORDER BY wins DESC, plays ASC, user_id ASC
         LIMIT 25
    """, (game,)).fetchall()

    leaders = []
    for row in rows:
        user = User.query.get(row["user_id"])
        if user:
            leaders.append({
                "name": user.username,
                "wins": int(row["wins"]),
                "plays": int(row["plays"]),
                "badge": badge_for_wins(int(row["wins"]))
            })

    return jsonify({"ok": True, "leaders": leaders})