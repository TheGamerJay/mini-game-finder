import sqlite3
import csv
import io
from pathlib import Path
from flask import Blueprint, g, render_template, jsonify, request, redirect, url_for, abort, current_app
from flask_login import login_required, current_user
from blueprints.credits import spend_credits, _get_user_id
from csrf_utils import require_csrf
from sqlalchemy import text

riddle_bp = Blueprint('riddle', __name__, url_prefix='/riddle')

# Credits system constants
FREE_RIDDLES_LIMIT = 5  # Number of free riddles per user
RIDDLE_COST = 5         # Credits required to play a riddle after free limit
REVEAL_COST = 5         # Credits required to reveal an answer

# Database setup for riddles
APP_DIR = Path(__file__).resolve().parent.parent
RIDDLE_DB_PATH = APP_DIR / "riddles.db"

def get_riddle_db():
    """Get riddle database connection"""
    if "riddle_db" not in g:
        g.riddle_db = sqlite3.connect(RIDDLE_DB_PATH)
        g.riddle_db.row_factory = sqlite3.Row
    return g.riddle_db

@riddle_bp.teardown_app_request
def close_riddle_db(error):
    """Close riddle database connection"""
    db = g.pop("riddle_db", None)
    if db is not None:
        db.close()

def init_riddle_db():
    """Initialize riddle database with schema and seed data"""
    new_db = not RIDDLE_DB_PATH.exists()
    db = sqlite3.connect(RIDDLE_DB_PATH)
    db.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS riddles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            hint TEXT,
            difficulty TEXT DEFAULT 'normal'
        );
        """
    )
    if new_db:
        seed = [
            ("What has to be broken before you can use it?",
             "egg|an egg|the egg",
             "Breakfast thoughts…",
             "easy"),
            ("I speak without a mouth and hear without ears. I have nobody, but I come alive with wind. What am I?",
             "echo|an echo|the echo",
             "You'll hear me in canyons.",
             "medium"),
            ("The more of this there is, the less you see. What is it?",
             "darkness|the dark|dark",
             "It shows up when the lights go out.",
             "easy"),
            ("What month has 28 days?",
             "all of them|all months|every month|all|all of em",
             "Trick question 😉",
             "easy"),
            ("I have branches, but no fruit, trunk or leaves. What am I?",
             "bank|a bank|the bank",
             "Not a tree.",
             "medium"),
            ("What gets wetter the more it dries?",
             "towel|a towel|the towel",
             "It hangs in the bathroom.",
             "easy"),
            ("What can you catch but not throw?",
             "cold|a cold|the cold",
             "You might need tissues.",
             "easy"),
            ("I'm tall when I'm young, and I'm short when I'm old. What am I?",
             "candle|a candle|the candle",
             "It gives light.",
             "easy"),
            ("What building has the most stories?",
             "library|a library|the library",
             "Full of books.",
             "medium"),
            ("What goes up but never comes down?",
             "age|your age",
             "Everyone has one that increases.",
             "easy"),
        ]
        db.executemany(
            "INSERT INTO riddles (question, answer, hint, difficulty) VALUES (?, ?, ?, ?)",
            seed,
        )
    db.commit()
    db.close()

# Initialize database when blueprint is imported
init_riddle_db()

# Utility functions
ARTICLES = ("a ", "an ", "the ")

def normalize(text: str) -> str:
    """Lowercase, trim, remove punctuation-like chars, collapse spaces, drop leading articles."""
    if text is None:
        return ""
    t = text.strip().lower()
    # remove common punctuation
    for ch in ",.?;:!\"'`~@#$%^&*()[]{}<>_/\\|-":
        t = t.replace(ch, " ")
    # collapse spaces
    t = " ".join(t.split())
    # remove leading articles once
    for art in ARTICLES:
        if t.startswith(art):
            t = t[len(art):]
            break
    return t

def is_correct(guess: str, answers_pipe: str) -> bool:
    """Check if guess matches any of the accepted answers"""
    guess_n = normalize(guess)
    for opt in (answers_pipe or "").split("|"):
        if guess_n == normalize(opt):
            return True
    return False

# Routes
@riddle_bp.route("/")
@login_required
def riddle_home():
    """Riddle game home page showing all riddles"""
    from models import db, User

    user_id = _get_user_id()
    if not user_id:
        return redirect(url_for('core.login'))

    # Get user data for credits info
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    # Handle missing riddles_played_free column
    try:
        riddles_played_free = user.riddles_played_free or 0
    except AttributeError:
        riddles_played_free = 0

    free_riddles_left = max(0, FREE_RIDDLES_LIMIT - riddles_played_free)

    riddle_db = get_riddle_db()
    rows = riddle_db.execute(
        "SELECT id, question, hint, difficulty FROM riddles ORDER BY id ASC"
    ).fetchall()

    return render_template("riddle/play.html",
                         riddles=rows,
                         free_riddles_left=free_riddles_left,
                         current_credits=user.mini_word_credits,
                         riddle_cost=RIDDLE_COST)

@riddle_bp.route("/<int:riddle_id>")
@login_required
def riddle_page(riddle_id: int):
    return show_riddle(riddle_id)

@riddle_bp.route("/<int:riddle_id>/<mode>")
@login_required
def show_riddle(riddle_id: int, mode=None):
    """Individual riddle page with credits system"""
    from models import db, User

    # Check if riddle exists
    riddle_db = get_riddle_db()
    row = riddle_db.execute(
        "SELECT id, question, hint, difficulty FROM riddles WHERE id = ?", (riddle_id,)
    ).fetchone()
    if not row:
        abort(404)

    user_id = _get_user_id()
    if not user_id:
        return redirect(url_for('core.login'))

    # Get user data
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    # Handle missing riddles_played_free column (migration not yet applied)
    try:
        riddles_played_free = user.riddles_played_free or 0
    except AttributeError:
        current_app.logger.warning("riddles_played_free column missing - using default 0")
        riddles_played_free = 0

    paid = False
    cost_credits = 0

    if riddles_played_free < FREE_RIDDLES_LIMIT:
        # Free riddle - increment counter
        try:
            user.riddles_played_free = riddles_played_free + 1
            db.session.commit()
            current_app.logger.info(f"User {user_id} played free riddle {riddles_played_free + 1}/{FREE_RIDDLES_LIMIT}")
        except AttributeError:
            # Column doesn't exist yet, skip the increment
            current_app.logger.warning("Cannot increment riddles_played_free - column missing")
        paid = False
        cost_credits = 0
    else:
        # Paid riddle - charge credits
        try:
            spend_credits(user_id, RIDDLE_COST, "riddle_play", riddle_id=riddle_id)
            paid = True
            cost_credits = RIDDLE_COST
            current_app.logger.info(f"User {user_id} played paid riddle for {RIDDLE_COST} credits")
        except ValueError as e:
            if "INSUFFICIENT_CREDITS" in str(e):
                return render_template("riddle/insufficient_credits.html",
                                     required=RIDDLE_COST,
                                     riddle=row,
                                     current_credits=user.mini_word_credits)
            else:
                raise

    return render_template("riddle/riddle.html", riddle=row, paid=paid, cost_credits=cost_credits)

# JSON APIs for AJAX flow
@riddle_bp.route("/api/<int:riddle_id>")
@login_required
def api_riddle(riddle_id: int):
    """Get riddle data as JSON"""
    db = get_riddle_db()
    row = db.execute(
        "SELECT id, question, hint, difficulty FROM riddles WHERE id = ?", (riddle_id,)
    ).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({
        "ok": True,
        "riddle": {
            "id": row["id"],
            "question": row["question"],
            "hint": row["hint"],
            "difficulty": row["difficulty"]
        }
    })

@riddle_bp.route("/api/<int:riddle_id>/check", methods=["POST"])
@login_required
@require_csrf
def api_check(riddle_id: int):
    """Check if answer is correct"""
    data = request.get_json(silent=True) or request.form
    guess = (data.get("guess") or "").strip()
    if not guess:
        return jsonify({"ok": False, "error": "Empty guess"}), 400

    db = get_riddle_db()
    row = db.execute(
        "SELECT id, answer FROM riddles WHERE id = ?", (riddle_id,)
    ).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Not found"}), 404

    correct = is_correct(guess, row["answer"])
    return jsonify({"ok": True, "correct": bool(correct)})

@riddle_bp.route("/api/<int:riddle_id>/reveal", methods=["POST"])
@login_required
@require_csrf
def api_reveal(riddle_id: int):
    """Reveal the answer for 5 credits"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"ok": False, "error": "Credits required but no user logged in"}), 401

    try:
        # Check if riddle exists
        riddle_db = get_riddle_db()
        row = riddle_db.execute(
            "SELECT id, answer FROM riddles WHERE id = ?", (riddle_id,)
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Riddle not found"}), 404

        # Charge credits for reveal
        try:
            spend_credits(user_id, REVEAL_COST, "riddle_reveal", riddle_id=riddle_id)
            current_app.logger.info(f"User {user_id} revealed riddle {riddle_id} for {REVEAL_COST} credits")
        except ValueError as e:
            if "INSUFFICIENT_CREDITS" in str(e):
                return jsonify({
                    "ok": False,
                    "error": "INSUFFICIENT_CREDITS",
                    "required": REVEAL_COST,
                    "message": f"You need {REVEAL_COST} credits to reveal the answer."
                }), 402
            else:
                raise

        # Return the answer
        answers = row["answer"].split("|")
        primary_answer = answers[0] if answers else "Unknown"

        return jsonify({
            "ok": True,
            "answer": primary_answer,
            "all_answers": answers,
            "cost": REVEAL_COST
        })

    except Exception as e:
        current_app.logger.error(f"Error revealing riddle {riddle_id}: {e}")
        return jsonify({"ok": False, "error": "Failed to reveal answer"}), 500

@riddle_bp.route("/api/<int:riddle_id>/neighbors")
@login_required
def api_neighbors(riddle_id: int):
    """Get previous and next riddle IDs"""
    db = get_riddle_db()
    ids = db.execute("SELECT id FROM riddles ORDER BY id ASC").fetchall()
    ids = [r["id"] for r in ids]
    if riddle_id not in ids:
        return jsonify({"ok": False, "error": "Not found"}), 404
    idx = ids.index(riddle_id)
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx < len(ids) - 1 else None
    return jsonify({"ok": True, "prev_id": prev_id, "next_id": next_id})

# Admin endpoints for content management
@riddle_bp.route("/admin/import", methods=["GET", "POST"])
@login_required
def admin_import():
    """CSV bulk import for riddles (admin only)"""
    from models import User

    user_id = _get_user_id()
    user = User.query.get(user_id)

    # Check if user is admin
    if not user or not user.is_admin:
        abort(403)

    if request.method == "GET":
        return render_template("riddle/admin_import.html")

    # Handle CSV upload
    if 'csv_file' not in request.files:
        return jsonify({"ok": False, "error": "No CSV file provided"}), 400

    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({"ok": False, "error": "No file selected"}), 400

    try:
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)

        imported_count = 0
        errors = []

        # Use main database for production
        from models import db

        for row_num, row in enumerate(csv_reader, start=2):
            try:
                question = row.get('question', '').strip()
                answer = row.get('answer', '').strip()
                hint = row.get('hint', '').strip()
                difficulty = row.get('difficulty', 'normal').strip().lower()

                if not question or not answer:
                    errors.append(f"Row {row_num}: Missing question or answer")
                    continue

                if difficulty not in ['easy', 'medium', 'hard', 'normal']:
                    difficulty = 'normal'

                # Insert into PostgreSQL
                db.session.execute(
                    "INSERT INTO riddles (question, answer, hint, difficulty) VALUES (%s, %s, %s, %s)",
                    (question, answer, hint, difficulty)
                )
                imported_count += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        # Commit all inserts
        db.session.commit()

        return jsonify({
            "ok": True,
            "imported": imported_count,
            "errors": errors
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": f"Import failed: {str(e)}"}), 500

# Procedural riddle generator
import random

# Template bank for endless riddle variations
RIDDLE_TEMPLATES = [
    {
        "template": "What has keys but opens no locks, has space but no room, and lets you enter yet goes nowhere?",
        "answers": ["keyboard", "a keyboard", "the keyboard"],
        "hint": "You use it every time you type.",
        "difficulty": "medium"
    },
    {
        "template": "The more you {verb}, the more you leave behind. What are they?",
        "answers": ["footsteps", "your footsteps", "steps"],
        "hint": "Think about walking.",
        "difficulty": "medium",
        "choices": {"verb": ["walk", "travel", "march", "run", "step"]}
    },
    {
        "template": "I have {n1} hands but no {n2}, a face but no {n3}. What am I?",
        "answers": ["clock", "a clock", "the clock"],
        "hint": "It tells time every minute.",
        "difficulty": "easy",
        "choices": {
            "n1": ["two", "many"],
            "n2": ["arms", "fingers", "body"],
            "n3": ["mouth", "eyes", "nose"]
        }
    },
    {
        "template": "I speak without a mouth and hear without ears. I have no body, but I come alive with {medium}. What am I?",
        "answers": ["echo", "an echo", "the echo"],
        "hint": "Canyons and mountains love me.",
        "difficulty": "medium",
        "choices": {"medium": ["sound", "wind", "noise", "music"]}
    },
    {
        "template": "I'm taken from a mine and shut up in a wooden case, from which I am never released, and yet I am used by almost every person. What am I?",
        "answers": ["pencil lead", "graphite", "lead", "pencil graphite"],
        "hint": "Think old-school writing tools.",
        "difficulty": "hard"
    },
    {
        "template": "It belongs to you, but others use it more than you do. What is it?",
        "answers": ["your name", "name", "my name"],
        "hint": "People say it to get your attention.",
        "difficulty": "easy"
    },
    {
        "template": "What gets {comp} the more it dries?",
        "answers": ["towel", "a towel", "the towel"],
        "hint": "Bathroom essential.",
        "difficulty": "easy",
        "choices": {"comp": ["wetter", "more wet", "soaked"]}
    },
    {
        "template": "I have {n1} legs in the morning, {n2} legs at noon, and {n3} legs in the evening. What am I?",
        "answers": ["human", "person", "man", "human being"],
        "hint": "Think about life stages.",
        "difficulty": "hard",
        "choices": {
            "n1": ["four", "4"],
            "n2": ["two", "2"],
            "n3": ["three", "3"]
        }
    }
]

def generate_riddle():
    """Generate a new riddle from templates"""
    template_data = random.choice(RIDDLE_TEMPLATES)

    question = template_data["template"]

    # Replace template variables if they exist
    if "choices" in template_data:
        for key, options in template_data["choices"].items():
            placeholder = "{" + key + "}"
            if placeholder in question:
                replacement = random.choice(options)
                question = question.replace(placeholder, replacement)

    return {
        "question": question,
        "answer": "|".join(template_data["answers"]),
        "hint": template_data["hint"],
        "difficulty": template_data["difficulty"]
    }

@riddle_bp.route("/api/generate", methods=["POST"])
@login_required
def api_generate_riddle():
    """Generate and save a new procedural riddle"""
    from models import db

    try:
        riddle_data = generate_riddle()

        # Insert into PostgreSQL
        db.session.execute(
            "INSERT INTO riddles (question, answer, hint, difficulty) VALUES (%s, %s, %s, %s)",
            (riddle_data["question"], riddle_data["answer"], riddle_data["hint"], riddle_data["difficulty"])
        )
        db.session.commit()

        # Get the ID of the newly created riddle
        result = db.session.execute(
            "SELECT id FROM riddles WHERE question = %s ORDER BY id DESC LIMIT 1",
            (riddle_data["question"],)
        )
        riddle_id = result.fetchone()[0]

        current_app.logger.info(f"Generated new riddle #{riddle_id}")

        return jsonify({
            "ok": True,
            "riddle_id": riddle_id,
            "question": riddle_data["question"],
            "hint": riddle_data["hint"],
            "difficulty": riddle_data["difficulty"]
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating riddle: {e}")
        return jsonify({"ok": False, "error": "Failed to generate riddle"}), 500

# Challenge Gate API endpoints
@riddle_bp.route("/api/gate/check", methods=["GET"])
@login_required
def api_gate_check():
    """Check if user has accepted the challenge gate"""
    from models import db

    try:
        result = db.session.execute(
            text("SELECT challenge_gate_accepted FROM users WHERE id = :user_id"),
            {"user_id": current_user.id}
        )
        row = result.fetchone()

        if row is None:
            return jsonify({"ok": False, "error": "User not found"}), 404

        return jsonify({
            "ok": True,
            "accepted": bool(row[0])
        })

    except Exception as e:
        current_app.logger.error(f"Error checking gate status: {e}")
        return jsonify({"ok": False, "error": "Failed to check gate status"}), 500

@riddle_bp.route("/api/gate/accept", methods=["POST"])
@login_required
def api_gate_accept():
    """Mark that user has accepted the challenge gate"""
    from models import db

    try:
        db.session.execute(
            text("UPDATE users SET challenge_gate_accepted = TRUE WHERE id = :user_id"),
            {"user_id": current_user.id}
        )
        db.session.commit()

        current_app.logger.info(f"User {current_user.id} accepted riddle challenge gate")

        return jsonify({
            "ok": True,
            "message": "Challenge gate accepted"
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error accepting gate: {e}")
        return jsonify({"ok": False, "error": "Failed to accept challenge gate"}), 500

# Difficulty Mode Routes
@riddle_bp.route("/mode/<difficulty>")
def riddle_mode(difficulty):
    """Browse riddles by difficulty mode"""
    if difficulty not in ['easy', 'medium', 'hard']:
        abort(404)

    # Get count for the difficulty
    db_conn = get_riddle_db()
    cursor = db_conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM riddles WHERE difficulty = ?", (difficulty,))
    total_count = cursor.fetchone()[0]

    # Get first riddle of this difficulty
    cursor.execute("SELECT id FROM riddles WHERE difficulty = ? ORDER BY id LIMIT 1", (difficulty,))
    first_riddle = cursor.fetchone()

    if not first_riddle:
        abort(404)

    # Redirect to the first riddle of this difficulty with mode parameter
    return redirect(url_for('riddle.show_riddle', riddle_id=first_riddle[0], mode=difficulty))

@riddle_bp.route("/challenge")
def challenge_mode():
    """Challenge mode with timer"""
    return render_template("riddle_challenge.html")

@riddle_bp.route("/api/challenge/start", methods=["POST"])
def api_start_challenge():
    """Start a new challenge session"""
    from random import choice

    db_conn = get_riddle_db()
    cursor = db_conn.cursor()

    # Get a random riddle for the challenge
    cursor.execute("SELECT id, question, answer, difficulty, hint FROM riddles ORDER BY RANDOM() LIMIT 1")
    riddle = cursor.fetchone()

    if not riddle:
        return jsonify({"ok": False, "error": "No riddles available"}), 404

    return jsonify({
        "ok": True,
        "riddle": {
            "id": riddle[0],
            "question": riddle[1],
            "answer": riddle[2],
            "difficulty": riddle[3],
            "hint": riddle[4]
        },
        "timer": 60  # 60 seconds for challenge mode
    })