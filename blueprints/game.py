# 🐍 Block B — Flask blueprints: Game API
# This blueprint handles game start (free/paid) and word reveal functionality

from flask import Blueprint, request, jsonify, abort, session, current_app
from models import db, User
from routes import get_session_user
from csrf_utils import require_csrf
from blueprints.credits import spend_credits, _get_db_connection, _get_user_id
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Game costs configuration
GAME_COST = 5        # Credits required to start a game after free games
REVEAL_COST = 5      # Credits required to reveal a word
FREE_GAMES_LIMIT = 5 # Number of free games per user

game_bp = Blueprint("game", __name__, url_prefix="/api/game")

@game_bp.route("/start", methods=["POST"])
@require_csrf
def start_game():
    """
    Start a game: first 5 are free, then 5 credits per game
    """
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json(force=True) or {}
    puzzle_id = data.get("puzzle_id")
    mode = data.get("mode", "easy")
    category = data.get("category")

    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check how many free games the user has played
                cur.execute("""
                    SELECT games_played_free FROM users WHERE id = %s FOR UPDATE
                """, (user_id,))
                user_row = cur.fetchone()

                if not user_row:
                    return jsonify({"error": "User not found"}), 404

                games_played_free = user_row["games_played_free"]
                paid = False
                cost_credits = 0

                if games_played_free < FREE_GAMES_LIMIT:
                    # Free game - increment counter
                    cur.execute("""
                        UPDATE users
                        SET games_played_free = games_played_free + 1
                        WHERE id = %s
                    """, (user_id,))
                    paid = False
                    cost_credits = 0
                    current_app.logger.info(f"User {user_id} started free game {games_played_free + 1}/{FREE_GAMES_LIMIT}")
                else:
                    # Paid game - charge credits
                    try:
                        spend_credits(user_id, GAME_COST, "game_start", puzzle_id=puzzle_id)
                        paid = True
                        cost_credits = GAME_COST
                        current_app.logger.info(f"User {user_id} started paid game for {GAME_COST} credits")
                    except ValueError as e:
                        if "INSUFFICIENT_CREDITS" in str(e):
                            return jsonify({
                                "ok": False,
                                "error": "INSUFFICIENT_CREDITS",
                                "required": GAME_COST,
                                "message": f"You need {GAME_COST} credits to start a game. Visit the Store to purchase credits."
                            }), 402
                        else:
                            raise

                # Create game session record
                cur.execute("""
                    INSERT INTO game_sessions (
                        user_id, puzzle_id, mode, category, cost_credits, status
                    ) VALUES (%s, %s, %s, %s, %s, 'active')
                    RETURNING id
                """, (user_id, puzzle_id, mode, category, cost_credits))

                session_id = cur.fetchone()["id"]

                # Get updated balance
                cur.execute("SELECT get_user_credits(%s) AS balance", (user_id,))
                balance = cur.fetchone()["balance"]

        return jsonify({
            "ok": True,
            "paid": paid,
            "cost": cost_credits,
            "session_id": session_id,
            "balance": balance,
            "free_games_remaining": max(0, FREE_GAMES_LIMIT - (games_played_free + 1)) if not paid else 0
        })

    except Exception as e:
        current_app.logger.error(f"Error starting game for user {user_id}: {e}")
        return jsonify({"error": "Failed to start game"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@game_bp.route("/reveal", methods=["POST"])
@require_csrf
def reveal_word():
    """
    Reveal a word: costs 5 credits, returns highlight path + lesson
    """
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json(force=True) or {}
    puzzle_id = data.get("puzzle_id")
    word_id = data.get("word_id")
    game_session_id = data.get("game_session_id")

    if not puzzle_id or not word_id:
        return jsonify({"error": "puzzle_id and word_id required"}), 400

    try:
        # Spend credits first (atomic operation)
        new_balance = spend_credits(user_id, REVEAL_COST, "reveal", puzzle_id=puzzle_id, word_id=word_id)

        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get word position and lesson data
                cur.execute("""
                    SELECT
                        pw.start_row, pw.start_col, pw.direction, pw.length,
                        w.text, w.definition, w.example, w.phonics,
                        w.difficulty_level, w.category
                    FROM puzzle_words pw
                    JOIN words w ON w.id = pw.word_id
                    WHERE pw.puzzle_id = %s AND pw.word_id = %s
                """, (puzzle_id, word_id))

                word_row = cur.fetchone()

                if not word_row:
                    # If not in puzzle_words table, try to find in words table
                    cur.execute("""
                        SELECT text, definition, example, phonics, difficulty_level, category
                        FROM words WHERE id = %s
                    """, (word_id,))
                    word_data = cur.fetchone()

                    if not word_data:
                        return jsonify({"error": "Word not found"}), 404

                    # Return lesson without path (for words not positioned in grid)
                    response_data = {
                        "ok": True,
                        "balance": new_balance,
                        "lesson": {
                            "word": word_data["text"],
                            "definition": word_data["definition"],
                            "example": word_data["example"],
                            "phonics": word_data["phonics"],
                            "difficulty": word_data["difficulty_level"],
                            "category": word_data["category"]
                        }
                    }
                else:
                    # Return both path and lesson
                    response_data = {
                        "ok": True,
                        "balance": new_balance,
                        "path": {
                            "start_row": word_row["start_row"],
                            "start_col": word_row["start_col"],
                            "direction": word_row["direction"],
                            "length": word_row["length"]
                        },
                        "lesson": {
                            "word": word_row["text"],
                            "definition": word_row["definition"],
                            "example": word_row["example"],
                            "phonics": word_row["phonics"],
                            "difficulty": word_row["difficulty_level"],
                            "category": word_row["category"]
                        }
                    }

                # Record the word reveal
                cur.execute("""
                    INSERT INTO word_reveals (
                        user_id, game_session_id, puzzle_id, word_id,
                        word_text, cost_credits, lesson_shown
                    ) VALUES (%s, %s, %s, %s, %s, %s, true)
                """, (user_id, game_session_id, puzzle_id, word_id,
                      word_row["text"] if word_row else word_data["text"], REVEAL_COST))

                current_app.logger.info(f"User {user_id} revealed word {word_id} for {REVEAL_COST} credits")

        return jsonify(response_data)

    except ValueError as e:
        if "INSUFFICIENT_CREDITS" in str(e):
            return jsonify({
                "ok": False,
                "error": "INSUFFICIENT_CREDITS",
                "required": REVEAL_COST,
                "message": f"You need {REVEAL_COST} credits to reveal a word. Visit the Store to purchase credits."
            }), 402
        else:
            current_app.logger.error(f"Error revealing word: {e}")
            return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Error revealing word for user {user_id}: {e}")
        return jsonify({"error": "Failed to reveal word"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@game_bp.route("/session/<int:session_id>/complete", methods=["POST"])
@require_csrf
def complete_game_session(session_id):
    """Mark a game session as completed with final score"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json() or {}
    words_found = int(data.get('words_found', 0))
    total_words = int(data.get('total_words', 0))
    score = int(data.get('score', 0))

    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Verify session belongs to user and update it
                cur.execute("""
                    UPDATE game_sessions
                    SET
                        status = 'completed',
                        words_found = %s,
                        total_words = %s,
                        score = %s,
                        completed_at = now()
                    WHERE id = %s AND user_id = %s AND status = 'active'
                    RETURNING id
                """, (words_found, total_words, score, session_id, user_id))

                if not cur.fetchone():
                    return jsonify({"error": "Game session not found or already completed"}), 404

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "final_score": score,
            "completion_rate": f"{words_found}/{total_words}"
        })

    except Exception as e:
        current_app.logger.error(f"Error completing game session {session_id}: {e}")
        return jsonify({"error": "Failed to complete game session"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@game_bp.route("/sessions", methods=["GET"])
def get_game_sessions():
    """Get user's recent game sessions"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    limit = min(int(request.args.get('limit', 20)), 50)

    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        id, puzzle_id, mode, category, cost_credits, status,
                        words_found, total_words, score,
                        started_at, completed_at
                    FROM game_sessions
                    WHERE user_id = %s
                    ORDER BY started_at DESC
                    LIMIT %s
                """, (user_id, limit))

                sessions = [dict(row) for row in cur.fetchall()]

        return jsonify({
            "ok": True,
            "sessions": sessions
        })

    except Exception as e:
        current_app.logger.error(f"Error getting game sessions for user {user_id}: {e}")
        return jsonify({"error": "Failed to get game sessions"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@game_bp.route("/costs", methods=["GET"])
def get_game_costs():
    """Get current game costs and user's free game status"""
    user_id = _get_user_id()

    # Return costs info (public info)
    response_data = {
        "ok": True,
        "costs": {
            "game_start": GAME_COST,
            "word_reveal": REVEAL_COST,
            "free_games_limit": FREE_GAMES_LIMIT
        }
    }

    # Add user-specific info if logged in
    if user_id:
        try:
            conn = _get_db_connection()
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT games_played_free, get_user_credits(%s) AS balance
                        FROM users WHERE id = %s
                    """, (user_id, user_id))

                    user_row = cur.fetchone()
                    if user_row:
                        free_games_used = user_row["games_played_free"]
                        response_data["user"] = {
                            "balance": user_row["balance"],
                            "free_games_used": free_games_used,
                            "free_games_remaining": max(0, FREE_GAMES_LIMIT - free_games_used),
                            "next_game_cost": 0 if free_games_used < FREE_GAMES_LIMIT else GAME_COST
                        }
        except Exception as e:
            current_app.logger.error(f"Error getting user game info: {e}")
            # Don't fail the whole request for user info
        finally:
            if 'conn' in locals():
                conn.close()

    return jsonify(response_data)