import os, secrets
from flask import Blueprint, g, render_template, request, jsonify, session, redirect, url_for
from blueprints.credits import spend_credits, _get_user_id
from models import db, User
import psycopg2
import psycopg2.extras

arcade_bp = Blueprint('arcade', __name__, url_prefix='/game')

CREDITS_PER_EXTRA_PLAY = 5  # after 5 free plays per game

def pg():
    """Get PostgreSQL connection"""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    # Handle Heroku postgres:// URLs
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(dsn, sslmode="require", cursor_factory=psycopg2.extras.DictCursor)

def get_uid():
    """Get user ID from current session/auth"""
    return _get_user_id()

def ensure_membership(conn, community_id, user_id):
    """Ensure user is member of community"""
    with conn.cursor() as cur:
        cur.execute("""
          INSERT INTO community_members(community_id, user_id)
          VALUES (%s, %s)
          ON CONFLICT (community_id, user_id) DO NOTHING
        """, (community_id, user_id))

def ensure_profile(conn, community_id, user_id, game):
    """Ensure user has a game profile in community"""
    with conn.cursor() as cur:
        cur.execute("""
          INSERT INTO game_profile(community_id, user_id, game_code)
          VALUES (%s, %s, %s)
          ON CONFLICT (community_id, user_id, game_code) DO NOTHING
        """, (community_id, user_id, game))

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
    """
    Start a game round - uses free play or charges credits
    Body: { "game": "ttt" | "c4", "community_id": 1 }
    """
    uid = get_uid()
    if not uid:
        return jsonify({"ok": False, "error": "not_logged_in"}), 401

    data = request.get_json(silent=True) or {}
    game = (data.get("game") or "").lower()
    community_id = int(data.get("community_id") or 1)

    if game not in ("ttt","c4"):
        return jsonify({"ok": False, "error": "invalid_game"}), 400

    charged = 0
    try:
        with pg() as conn:
            conn.autocommit = False
            ensure_membership(conn, community_id, uid)
            ensure_profile(conn, community_id, uid, game)

            with conn.cursor() as cur:
                cur.execute("""
                  SELECT free_remaining FROM game_profile
                   WHERE community_id=%s AND user_id=%s AND game_code=%s
                   FOR UPDATE
                """, (community_id, uid, game))
                result = cur.fetchone()
                free_remaining = int(result["free_remaining"]) if result else 5

                if free_remaining > 0:
                    free_remaining -= 1
                    cur.execute("""
                      UPDATE game_profile
                         SET free_remaining=%s, last_play_at=NOW()
                       WHERE community_id=%s AND user_id=%s AND game_code=%s
                    """, (free_remaining, community_id, uid, game))
                else:
                    # Spend credits using PostgreSQL function
                    ref = f"{game}:play:{uid}:{secrets.token_hex(4)}"
                    try:
                        cur.execute("SELECT apply_credit_delta(%s,%s,%s,%s,%s)",
                            (uid, -CREDITS_PER_EXTRA_PLAY, f"{game}_play", ref, community_id))
                        charged = CREDITS_PER_EXTRA_PLAY
                    except psycopg2.Error as e:
                        if "INSUFFICIENT_CREDITS" in str(e):
                            user = User.query.get(uid)
                            credits = user.mini_word_credits if user else 0
                            return jsonify({"ok": False, "error": "insufficient_credits", "credits": credits}), 400
                        raise

                conn.commit()

            # Get updated info
            with conn.cursor() as cur:
                cur.execute("SELECT mini_word_credits FROM users WHERE id=%s", (uid,))
                credits = int(cur.fetchone()["mini_word_credits"])
                cur.execute("""
                  SELECT free_remaining FROM game_profile
                   WHERE community_id=%s AND user_id=%s AND game_code=%s
                """, (community_id, uid, game))
                free_remaining = int(cur.fetchone()["free_remaining"])

        return jsonify({"ok": True, "community_id": community_id,
                        "free_remaining": free_remaining, "charged": charged, "credits": credits})

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