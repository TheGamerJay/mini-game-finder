# 🐍 Block B — Flask blueprints: Game API
# This blueprint handles game start (free/paid) and word reveal functionality

from flask import Blueprint, request, jsonify, abort, session, current_app
from models import db, User
from routes import get_session_user
from csrf_utils import require_csrf
from blueprints.credits import spend_credits, _get_user_id
from datetime import datetime

# Word definitions for lessons (shared with reveal system)
WORD_DEFINITIONS = {
    "BOARD": {"def": "A flat piece of wood, plastic, or other material used for various purposes", "example": "We wrote on the board with chalk."},
    "MOON": {"def": "Earth's natural satellite that orbits around our planet", "example": "The moon shines brightly in the night sky."},
    "SEARCH": {"def": "To look for something carefully", "example": "I will search for my lost keys."},
    "MOUNTAIN": {"def": "A large natural elevation of land rising above the surrounding area", "example": "We climbed the mountain to see the view."},
    "OCEAN": {"def": "A very large body of salt water", "example": "The Pacific Ocean is the largest ocean on Earth."},
    "TREE": {"def": "A woody plant that is typically tall with a trunk and branches", "example": "Birds nest in the old oak tree."},
    "HOUSE": {"def": "A building where people live", "example": "My house has a red door."},
    "WATER": {"def": "A clear liquid that is essential for life", "example": "Please drink more water to stay healthy."},
    "LIGHT": {"def": "Brightness that allows us to see things", "example": "Turn on the light so we can read."},
    "BOOK": {"def": "A set of printed pages bound together", "example": "I'm reading an interesting book about space."},
    "FIRE": {"def": "The process of combustion that produces heat and light", "example": "We warmed our hands by the fire."},
    "RIVER": {"def": "A large stream of water flowing toward the sea", "example": "The river flows through the valley."},
    "CLOUD": {"def": "A visible mass of water droplets in the sky", "example": "The white cloud drifted across the blue sky."},
    "STONE": {"def": "A hard solid mineral matter", "example": "We skipped stones across the lake."},
    "BIRD": {"def": "A warm-blooded animal with feathers and wings", "example": "The bird built a nest in the tree."}
}

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
        # Use SQLAlchemy for database operations
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Handle missing games_played_free column (migration not yet applied)
        try:
            games_played_free = user.games_played_free or 0
        except AttributeError:
            current_app.logger.warning("games_played_free column missing - using default 0")
            games_played_free = 0
        paid = False
        cost_credits = 0
        session_id = None

        if games_played_free < FREE_GAMES_LIMIT:
            # Free game - increment counter
            try:
                user.games_played_free = games_played_free + 1
            except AttributeError:
                # Column doesn't exist yet, skip the increment
                current_app.logger.warning("Cannot increment games_played_free - column missing")
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

        # Commit user changes
        db.session.commit()

        # Generate a simple session ID (in a real implementation, you'd use a proper session table)
        import random
        session_id = random.randint(100000, 999999)

        # Get updated balance
        balance = user.mini_word_credits or 0

        return jsonify({
            "ok": True,
            "paid": paid,
            "cost": cost_credits,
            "session_id": session_id,
            "balance": balance,
            "free_games_remaining": max(0, FREE_GAMES_LIMIT - (getattr(user, 'games_played_free', 0) or 0)) if not paid else max(0, FREE_GAMES_LIMIT - (games_played_free + 1))
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error starting game for user {user_id}: {e}")
        return jsonify({"error": "Failed to start game"}), 500

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

        # Provide lesson based on the word_id (which is actually the word text)
        word_text = str(word_id).upper()

        # Get definition or use generic one
        word_info = WORD_DEFINITIONS.get(word_text, {
            "def": f"A word commonly found in word search puzzles",
            "example": f"The word {word_text} can be found in many vocabulary lists."
        })

        lesson_data = {
            "word": word_text,
            "definition": word_info["def"],
            "example": word_info["example"],
            "phonics": word_text.lower(),
            "difficulty": "medium",
            "category": "general"
        }

        # Create mock path data (random positioning for demonstration)
        import random
        path_data = [
            {"row": random.randint(0, 9), "col": random.randint(0, 9)}
            for _ in range(len(word_text))
        ]

        response_data = {
            "ok": True,
            "balance": new_balance,
            "path": path_data,
            "lesson": lesson_data
        }

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

    # For now, just log the completion (in a full implementation, this would update a game_sessions table)
    current_app.logger.info(f"User {user_id} completed game session {session_id}: {words_found}/{total_words} words, score: {score}")

    return jsonify({
        "ok": True,
        "session_id": session_id,
        "final_score": score,
        "completion_rate": f"{words_found}/{total_words}"
    })

@game_bp.route("/sessions", methods=["GET"])
def get_game_sessions():
    """Get user's recent game sessions"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    # Return empty sessions for now (in a full implementation, this would query a game_sessions table)
    return jsonify({
        "ok": True,
        "sessions": []
    })

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
            user = db.session.get(User, user_id)
            if user:
                free_games_used = getattr(user, 'games_played_free', 0) or 0
                response_data["user"] = {
                    "balance": user.mini_word_credits or 0,
                    "free_games_used": free_games_used,
                    "free_games_remaining": max(0, FREE_GAMES_LIMIT - free_games_used),
                    "next_game_cost": 0 if free_games_used < FREE_GAMES_LIMIT else GAME_COST
                }
        except Exception as e:
            current_app.logger.error(f"Error getting user game info: {e}")
            # Don't fail the whole request for user info

    return jsonify(response_data)

