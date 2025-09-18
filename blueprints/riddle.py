import sqlite3
from pathlib import Path
from flask import Blueprint, g, render_template, jsonify, request, redirect, url_for, abort, current_app
from flask_login import login_required, current_user
from blueprints.credits import spend_credits, _get_user_id

riddle_bp = Blueprint('riddle', __name__, url_prefix='/riddle')

# Credits system constants
FREE_RIDDLES_LIMIT = 5  # Number of free riddles per user
RIDDLE_COST = 5         # Credits required to play a riddle after free limit

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