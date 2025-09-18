# 🐍 Block B — Flask blueprints: Game API
# This blueprint handles game start (free/paid) and word reveal functionality

from flask import Blueprint, request, jsonify, abort, session, current_app
from models import db, User, PuzzleBank
from routes import get_session_user
from csrf_utils import require_csrf
from blueprints.credits import spend_credits, _get_user_id
from datetime import datetime, date
import json

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

def find_word_in_grid(grid, word):
    """Find the position of a word in the puzzle grid"""
    if not grid or not word:
        return None

    word = word.upper()
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    # All 8 directions: right, down, diagonal-down-right, diagonal-down-left,
    # left, up, diagonal-up-left, diagonal-up-right
    directions = [
        (0, 1),   # right
        (1, 0),   # down
        (1, 1),   # diagonal-down-right
        (1, -1),  # diagonal-down-left
        (0, -1),  # left
        (-1, 0),  # up
        (-1, -1), # diagonal-up-left
        (-1, 1)   # diagonal-up-right
    ]

    def check_word_at_position(start_row, start_col, dr, dc):
        """Check if word exists starting at position in given direction"""
        path = []
        for i in range(len(word)):
            r = start_row + i * dr
            c = start_col + i * dc

            if r < 0 or r >= rows or c < 0 or c >= cols:
                return None

            if grid[r][c].upper() != word[i]:
                return None

            path.append({"row": r, "col": c})

        return path

    # Search every position and direction
    for row in range(rows):
        for col in range(cols):
            for dr, dc in directions:
                path = check_word_at_position(row, col, dr, dc)
                if path:
                    return path

    return None

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

        # Get current puzzle data to find the actual word position
        puzzle_data = None

        # Try to get puzzle from session first
        for key in session:
            if key.startswith('puzzle_') and not session.get(f"{key}_completed", False):
                puzzle_data = session[key]
                break

        # If no session puzzle, we can't reveal (shouldn't happen in normal flow)
        if not puzzle_data:
            return jsonify({"error": "No active puzzle found"}), 400

        # Find the actual word position in the grid
        path_data = find_word_in_grid(puzzle_data.get('grid', []), word_text)

        if not path_data:
            current_app.logger.warning(f"Could not find word {word_text} in puzzle grid")
            # Fallback to empty path if word not found
            path_data = []

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

@game_bp.route("/progress/save", methods=["POST"])
@require_csrf
def save_game_progress():
    """Save game progress to database"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json(force=True) or {}

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get existing preferences or create new dict
        try:
            preferences = json.loads(user.user_preferences or '{}')
        except (json.JSONDecodeError, TypeError):
            preferences = {}

        # Add game progress to preferences
        if 'game_progress' not in preferences:
            preferences['game_progress'] = {}

        game_key = f"{data.get('mode', 'easy')}_{data.get('daily', False)}"
        preferences['game_progress'][game_key] = {
            'puzzle': data.get('puzzle'),
            'found': data.get('found', []),
            'foundCells': data.get('foundCells', []),
            'startTime': data.get('startTime'),
            'timeLimit': data.get('timeLimit'),
            'mode': data.get('mode'),
            'isDaily': data.get('isDaily'),
            'category': data.get('category'),
            'timestamp': int(datetime.now().timestamp() * 1000)
        }

        # Save back to database
        user.user_preferences = json.dumps(preferences)
        db.session.commit()

        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving game progress: {e}")
        return jsonify({"error": "Failed to save progress"}), 500

@game_bp.route("/progress/load", methods=["GET"])
def load_game_progress():
    """Load game progress from database"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    mode = request.args.get('mode', 'easy')
    daily = request.args.get('daily') == 'true'

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get preferences
        try:
            preferences = json.loads(user.user_preferences or '{}')
        except (json.JSONDecodeError, TypeError):
            preferences = {}

        game_progress = preferences.get('game_progress', {})
        game_key = f"{mode}_{daily}"

        if game_key not in game_progress:
            return jsonify({"ok": True, "progress": None})

        progress = game_progress[game_key]

        # Check if progress is not too old (6 hours for regular, 24h for daily)
        max_age = 24 * 60 * 60 * 1000 if daily else 6 * 60 * 60 * 1000
        age = int(datetime.now().timestamp() * 1000) - progress.get('timestamp', 0)

        if age > max_age:
            # Remove expired progress
            del game_progress[game_key]
            user.user_preferences = json.dumps(preferences)
            db.session.commit()
            return jsonify({"ok": True, "progress": None})

        return jsonify({"ok": True, "progress": progress})

    except Exception as e:
        current_app.logger.error(f"Error loading game progress: {e}")
        return jsonify({"error": "Failed to load progress"}), 500

@game_bp.route("/progress/clear", methods=["POST"])
@require_csrf
def clear_game_progress():
    """Clear game progress from database"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    mode = request.args.get('mode', 'easy')
    daily = request.args.get('daily') == 'true'

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get preferences
        try:
            preferences = json.loads(user.user_preferences or '{}')
        except (json.JSONDecodeError, TypeError):
            preferences = {}

        game_progress = preferences.get('game_progress', {})
        game_key = f"{mode}_{daily}"

        if game_key in game_progress:
            del game_progress[game_key]
            user.user_preferences = json.dumps(preferences)
            db.session.commit()

        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing game progress: {e}")
        return jsonify({"error": "Failed to clear progress"}), 500

