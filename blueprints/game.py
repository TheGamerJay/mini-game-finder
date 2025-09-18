# 🐍 Block B — Flask blueprints: Game API
# This blueprint handles game start (free/paid) and word reveal functionality

from flask import Blueprint, request, jsonify, abort, session, current_app
from models import db, User, PuzzleBank
from routes import get_session_user
from csrf_utils import require_csrf
from blueprints.credits import spend_credits, _get_user_id
from datetime import datetime, date
import json
import hashlib
from sqlalchemy import text

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

# Progress validation limits
MAX_FOUND_WORDS = 300
MAX_FOUND_CELLS = 10000
MAX_PUZZLE_SIZE = 200 * 1024  # 200KB

def validate_progress_payload(data):
    """Validate and sanitize progress payload"""
    if not isinstance(data, dict):
        raise ValueError("Payload must be an object")

    # Validate required fields
    mode = data.get('mode')
    if mode not in ('easy', 'medium', 'hard'):
        raise ValueError(f"Invalid mode: {mode}")

    daily = data.get('isDaily')
    if not isinstance(daily, bool):
        raise ValueError("isDaily must be boolean")

    # Validate optional arrays with size limits
    found = data.get('found', [])
    if not isinstance(found, list) or len(found) > MAX_FOUND_WORDS:
        raise ValueError(f"found must be array with ≤ {MAX_FOUND_WORDS} items")

    found_cells = data.get('foundCells', [])
    if not isinstance(found_cells, list) or len(found_cells) > MAX_FOUND_CELLS:
        raise ValueError(f"foundCells must be array with ≤ {MAX_FOUND_CELLS} items")

    # Validate puzzle size
    puzzle = data.get('puzzle')
    if puzzle:
        puzzle_size = len(json.dumps(puzzle))
        if puzzle_size > MAX_PUZZLE_SIZE:
            raise ValueError(f"Puzzle too large: {puzzle_size} bytes")

    # Clean payload - only keep allowed fields
    cleaned = {
        'puzzle': puzzle,
        'found': found,
        'foundCells': found_cells,
        'startTime': data.get('startTime'),
        'timeLimit': data.get('timeLimit'),
        'mode': mode,
        'isDaily': daily,
        'category': data.get('category')
    }

    return cleaned

def compute_etag(user_id, key):
    """Compute ETag for progress data"""
    try:
        result = db.session.execute(
            text("SELECT user_preferences #> ARRAY['game_progress', :key] as progress FROM users WHERE id = :user_id"),
            {"user_id": user_id, "key": key}
        ).fetchone()

        if result and result.progress:
            content = json.dumps(result.progress, sort_keys=True)
            return hashlib.md5(content.encode()).hexdigest()
        return "empty"
    except Exception:
        return "error"

def prune_expired_progress(user_id):
    """Remove expired game progress entries"""
    try:
        # Use server time to determine expiry
        db.session.execute(text("""
            WITH progress_entries AS (
                SELECT key, value
                FROM jsonb_each(COALESCE(user_preferences->'game_progress', '{}'::jsonb))
            ),
            valid_entries AS (
                SELECT key, value
                FROM progress_entries
                WHERE (
                    (key LIKE '%_true' AND
                     (value->>'timestamp')::bigint >= EXTRACT(epoch FROM NOW() - INTERVAL '24 hours') * 1000) OR
                    (key LIKE '%_false' AND
                     (value->>'timestamp')::bigint >= EXTRACT(epoch FROM NOW() - INTERVAL '6 hours') * 1000)
                )
            )
            UPDATE users
            SET user_preferences = jsonb_set(
                COALESCE(user_preferences, '{}'::jsonb),
                '{game_progress}',
                COALESCE((SELECT jsonb_object_agg(key, value) FROM valid_entries), '{}'::jsonb)
            )
            WHERE id = :user_id
        """), {"user_id": user_id})
        db.session.commit()
    except Exception as e:
        current_app.logger.warning(f"Failed to prune expired progress for user {user_id}: {e}")
        db.session.rollback()

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
    """Save game progress to database with atomic JSONB operations"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    try:
        # Validate and clean payload
        data = request.get_json(force=True) or {}
        cleaned_data = validate_progress_payload(data)

        # Generate game key
        game_key = f"{cleaned_data['mode']}_{str(cleaned_data['isDaily']).lower()}"

        # Optional: Check ETag for concurrency control
        if_match = request.headers.get('If-Match')
        if if_match:
            current_etag = compute_etag(user_id, game_key)
            if current_etag != if_match:
                return jsonify({"error": "Conflict: progress was modified by another session"}), 412

        # Database-agnostic update using ORM
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Parse existing preferences
        try:
            preferences = json.loads(user.user_preferences or '{}')
        except (json.JSONDecodeError, TypeError):
            preferences = {}

        # Update game progress with timestamp
        if 'game_progress' not in preferences:
            preferences['game_progress'] = {}

        cleaned_data['timestamp'] = int(datetime.utcnow().timestamp() * 1000)
        preferences['game_progress'][game_key] = cleaned_data

        # Save back to database
        user.user_preferences = json.dumps(preferences)
        db.session.commit()

        # Compute new ETag
        new_etag = compute_etag(user_id, game_key)
        server_time = datetime.now().isoformat() + 'Z'

        return jsonify({
            "ok": True,
            "etag": new_etag,
            "savedAt": server_time,
            "key": game_key
        }), 200, {"ETag": new_etag}

    except ValueError as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving game progress for user {user_id}: {e}")
        return jsonify({"error": "Failed to save progress"}), 500

@game_bp.route("/progress/load", methods=["GET"])
def load_game_progress():
    """Load game progress from database with pruning"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    # Validate parameters
    mode = request.args.get('mode', 'easy')
    if mode not in ('easy', 'medium', 'hard'):
        return jsonify({"error": "Invalid mode"}), 400

    daily = request.args.get('daily', 'false').lower() == 'true'
    game_key = f"{mode}_{str(daily).lower()}"

    try:
        # Prune expired entries first
        prune_expired_progress(user_id)

        # Load specific progress entry
        result = db.session.execute(text("""
            SELECT user_preferences #> ARRAY['game_progress', :key] as progress
            FROM users WHERE id = :user_id
        """), {"user_id": user_id, "key": game_key})

        row = result.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404

        progress = row.progress if row.progress else None
        etag = compute_etag(user_id, game_key) if progress else "empty"
        server_time = datetime.now().isoformat() + 'Z'

        return jsonify({
            "ok": True,
            "progress": progress,
            "etag": etag,
            "serverNow": server_time
        }), 200, {"ETag": etag}

    except Exception as e:
        current_app.logger.error(f"Error loading game progress for user {user_id}: {e}")
        return jsonify({"error": "Failed to load progress"}), 500

@game_bp.route("/progress/clear", methods=["POST"])
@require_csrf
def clear_game_progress():
    """Clear game progress from database using atomic JSONB operations"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    mode = request.args.get('mode', 'easy')
    daily = request.args.get('daily') == 'true'
    game_key = f"{mode}_{daily}"

    try:
        # Database-agnostic removal using ORM
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Parse existing preferences
        try:
            preferences = json.loads(user.user_preferences or '{}')
        except (json.JSONDecodeError, TypeError):
            preferences = {}

        # Remove game progress if it exists
        if 'game_progress' in preferences and game_key in preferences['game_progress']:
            del preferences['game_progress'][game_key]
            user.user_preferences = json.dumps(preferences)

        db.session.commit()
        current_app.logger.info(f"Cleared progress for user {user_id}, game {game_key}")

        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing game progress: {e}")
        return jsonify({"error": "Failed to clear progress"}), 500

