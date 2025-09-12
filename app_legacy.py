import os, sqlite3, datetime, secrets
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, g, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    from urllib.parse import urlparse
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# puzzle generator (make sure puzzles.py exists)
from puzzles import make_puzzle

APP_NAME   = os.environ.get("APP_NAME", "Mini Word Finder")
SECRET_KEY = os.environ.get("FLASK_SECRET", os.environ.get("SECRET_KEY", secrets.token_hex(32)))
DATABASE_URL = os.environ.get("DATABASE_URL")
DB_PATH    = os.environ.get("DB_PATH", "app.db")

# Game modes (board size / words / timer seconds: 0 = no timer)
MODES = {
    "easy":   {"rows": 10, "cols": 10, "words": 5,  "seconds": 0},
    "medium": {"rows": 12, "cols": 12, "words": 7,  "seconds": 120},
    "hard":   {"rows": 14, "cols": 14, "words": 10, "seconds": 180},
}

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ---------------------- DB helpers ----------------------
def get_db():
    if "db" not in g:
        if DATABASE_URL and POSTGRES_AVAILABLE:
            # Use PostgreSQL
            g.db = psycopg2.connect(DATABASE_URL)
            g.db.cursor_factory = psycopg2.extras.RealDictCursor
        else:
            # Use SQLite
            g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
            g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = get_db()
    
    if DATABASE_URL and POSTGRES_AVAILABLE:
        # PostgreSQL schema
        with db.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users(
                  id SERIAL PRIMARY KEY,
                  email VARCHAR(255) UNIQUE NOT NULL,
                  password_hash VARCHAR(255) NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scores(
                  id SERIAL PRIMARY KEY,
                  user_id INTEGER NOT NULL,
                  mode VARCHAR(50) NOT NULL,
                  score INTEGER NOT NULL,
                  elapsed INTEGER,
                  seed VARCHAR(255),
                  note TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id)
                );
            """)
        db.commit()
    else:
        # SQLite schema
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scores(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          mode TEXT NOT NULL,
          score INTEGER NOT NULL,
          elapsed INTEGER,
          seed TEXT,
          note TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        db.commit()

def db_execute(query, params=None):
    """Execute a query with proper parameter substitution for both DB types"""
    db = get_db()
    if DATABASE_URL and POSTGRES_AVAILABLE:
        # PostgreSQL uses %s placeholders
        pg_query = query.replace('?', '%s')
        with db.cursor() as cur:
            cur.execute(pg_query, params or ())
            return cur
    else:
        # SQLite uses ? placeholders
        return db.execute(query, params or ())

def db_fetchone(query, params=None):
    """Fetch one row with proper parameter substitution"""
    db = get_db()
    if DATABASE_URL and POSTGRES_AVAILABLE:
        pg_query = query.replace('?', '%s')
        with db.cursor() as cur:
            cur.execute(pg_query, params or ())
            return cur.fetchone()
    else:
        return db.execute(query, params or ()).fetchone()

def db_fetchall(query, params=None):
    """Fetch all rows with proper parameter substitution"""
    db = get_db()
    if DATABASE_URL and POSTGRES_AVAILABLE:
        pg_query = query.replace('?', '%s')
        with db.cursor() as cur:
            cur.execute(pg_query, params or ())
            return cur.fetchall()
    else:
        return db.execute(query, params or ()).fetchall()

def db_commit():
    """Commit the current transaction"""
    get_db().commit()

@app.before_request
def _ensure_db():
    init_db()


# ---------------------- Auth helpers ----------------------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "uid" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper

def signer():
    return URLSafeTimedSerializer(SECRET_KEY)


# ---------------------- Routes: basics ----------------------
@app.route("/")
def index():
    return redirect(url_for("home") if "uid" in session else url_for("login"))

@app.route("/home")
@login_required
def home():
    return render_template("home.html", app_name=APP_NAME)


# ---------------------- Routes: auth ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw    = request.form.get("password", "")

        if not email or len(pw) < 6:
            msg = ("err", "Enter a valid email and a password with at least 6 characters.")
        else:
            try:
                db_execute("INSERT INTO users(email,password_hash) VALUES(?,?)",
                           (email, generate_password_hash(pw)))
                db_commit()
                flash("Account created. You can log in now.", "ok")
                return redirect(url_for("login"))
            except Exception as e:
                if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                    msg = ("err", "Email already registered.")
                else:
                    msg = ("err", "Registration failed. Please try again.")
    return render_template("register.html", app_name=APP_NAME, flash_msg=msg)

@app.route("/login", methods=["GET", "POST"])
def login():
    msg = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pw    = request.form.get("password", "")
        row = db_fetchone("SELECT id, password_hash FROM users WHERE email=?", (email,))
        if row and check_password_hash(row["password_hash"], pw):
            session["uid"] = row["id"]
            session["email"] = email
            return redirect(url_for("home"))
        msg = ("err", "Invalid email or password.")
    return render_template("login.html", app_name=APP_NAME, flash_msg=msg)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------- Routes: password reset (dev-friendly) ----------------------
# Uses the existing template 'reset_token.html' for both the request & reset steps.
@app.route("/reset", methods=["GET", "POST"])
def reset_request():
    msg = None
    dev_link = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = db_fetchone("SELECT id FROM users WHERE email=?", (email,))
        if user:
            token = signer().dumps(email)
            base  = os.environ.get("RESET_BASE_URL", request.host_url.rstrip("/"))
            dev_link = f"{base}{url_for('reset_with_token', token=token)}"
            msg = ("ok", "Reset link generated (dev mode).")
        else:
            msg = ("err", "Email not found.")
    # Render same template but in 'request' mode
    return render_template("reset_token.html", app_name=APP_NAME, request_mode=True,
                           flash_msg=msg, dev_link=dev_link)

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_with_token(token):
    msg = None
    email = None
    try:
        email = signer().loads(token, max_age=3600)
    except (BadSignature, SignatureExpired):
        msg = ("err", "Invalid or expired token.")

    if request.method == "POST" and email:
        pw = request.form.get("password", "")
        if len(pw) < 6:
            msg = ("err", "Password must be at least 6 characters.")
        else:
            db_execute("UPDATE users SET password_hash=? WHERE email=?",
                       (generate_password_hash(pw), email))
            db_commit()
            flash("Password updated. You can log in.", "ok")
            return redirect(url_for("login"))

    return render_template("reset_token.html", app_name=APP_NAME, request_mode=False,
                           flash_msg=msg)


# ---------------------- Game helpers ----------------------
def today_seed(mode: str) -> int:
    d = datetime.date.today().isoformat()
    return abs(hash(f"{d}:{mode}")) % (10**9)


# ---------------------- Routes: game & boards ----------------------
@app.route("/play/<mode>")
@login_required
def play(mode):
    if mode not in MODES:
        return redirect(url_for("home"))
    cfg = MODES[mode]
    seed = secrets.randbelow(10**9)
    grid, words = make_puzzle(cfg["rows"], cfg["cols"], cfg["words"], seed=seed)

    return render_template(
        "game.html",
        app_name=APP_NAME,
        mode=mode,
        seed=seed,
        grid=grid,
        words=words,
        seconds=cfg["seconds"],
    )

@app.route("/daily/<mode>")
@login_required
def daily(mode):
    if mode not in MODES:
        return redirect(url_for("home"))
    cfg = MODES[mode]
    seed = today_seed(mode)
    grid, words = make_puzzle(cfg["rows"], cfg["cols"], cfg["words"], seed=seed)
    return render_template(
        "game.html",
        app_name=APP_NAME,
        mode=mode,
        seed=seed,
        grid=grid,
        words=words,
        seconds=cfg["seconds"],
    )

@app.route("/seed/<mode>/<int:seed>")
@login_required
def seed_play(mode, seed):
    if mode not in MODES:
        return redirect(url_for("home"))
    cfg = MODES[mode]
    grid, words = make_puzzle(cfg["rows"], cfg["cols"], cfg["words"], seed=seed)
    return render_template(
        "game.html",
        app_name=APP_NAME,
        mode=mode,
        seed=seed,
        grid=grid,
        words=words,
        seconds=cfg["seconds"],
    )

@app.route("/submit-score", methods=["POST"])
@login_required
def submit_score():
    mode    = request.form.get("mode", "easy")
    elapsed = int(request.form.get("elapsed", "0") or 0)
    score   = int(request.form.get("score", "0") or 0)
    seed    = request.form.get("seed", "")
    note    = (request.form.get("note", "") or "")[:140]

    db_execute(
        "INSERT INTO scores(user_id, mode, score, elapsed, seed, note) VALUES(?,?,?,?,?,?)",
        (session["uid"], mode, score, elapsed if elapsed > 0 else None, str(seed), note)
    )
    db_commit()
    return redirect(url_for("leaderboard"))

@app.route("/leaderboard")
@login_required
def leaderboard():
    leaders = {}
    for m in MODES.keys():
        rows = db_fetchall("""
            SELECT s.score, s.elapsed, s.note, s.created_at, u.email
            FROM scores s JOIN users u ON u.id = s.user_id
            WHERE s.mode = ?
            ORDER BY s.score DESC, s.elapsed ASC NULLS LAST, s.created_at ASC
            LIMIT 20
        """, (m,))
        leaders[m] = [dict(r) for r in rows]
    return render_template("leaderboard.html", app_name=APP_NAME, leaders=leaders)

@app.route("/daily-leaderboard")
@login_required
def daily_leaderboard():
    today = datetime.date.today()
    dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(7)]
    day = request.args.get("day", dates[0])

    leaders = {}
    for m in MODES.keys():
        seed = abs(hash(f"{day}:{m}")) % (10**9)
        rows = db_fetchall("""
            SELECT s.score, s.elapsed, s.note, s.created_at, u.email
            FROM scores s JOIN users u ON u.id = s.user_id
            WHERE s.mode = ? AND s.seed = ?
            ORDER BY s.score DESC, s.elapsed ASC NULLS LAST, s.created_at ASC
            LIMIT 20
        """, (m, str(seed)))
        leaders[m] = [dict(r) for r in rows]

    return render_template("daily_leaderboard.html", app_name=APP_NAME,
                           leaders=leaders, dates=dates, day=day)


# ---------------------- Run ----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)