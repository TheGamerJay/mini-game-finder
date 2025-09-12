import os, secrets, datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import text

# Import our models and database setup
from models import init_db, db, User, Score
# puzzle generator (make sure puzzles.py exists)
from puzzles import make_puzzle

APP_NAME = os.environ.get("APP_NAME", "Mini Word Finder")
SECRET_KEY = os.environ.get("FLASK_SECRET", os.environ.get("SECRET_KEY", secrets.token_hex(32)))

# Game modes (board size / words / timer seconds: 0 = no timer)
MODES = {
    "easy": {"rows": 10, "cols": 10, "words": 5, "seconds": 0},
    "medium": {"rows": 12, "cols": 12, "words": 7, "seconds": 120},
    "hard": {"rows": 14, "cols": 14, "words": 10, "seconds": 180},
}


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # Initialize database with SQLAlchemy
    init_db(app, echo=False)

    # Health check routes for Railway
    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/debug/db-ping")
    def db_ping():
        try:
            db.session.execute(text("SELECT 1"))
            return {"db": "ok"}
        except Exception as e:
            return {"db": "error", "detail": str(e)}, 500

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
            pw = request.form.get("password", "")

            if not email or len(pw) < 6:
                msg = ("err", "Enter a valid email and a password with at least 6 characters.")
            else:
                # Check if user already exists
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    msg = ("err", "Email already registered.")
                else:
                    try:
                        # Create new user
                        user = User(email=email)
                        user.set_password(pw)
                        db.session.add(user)
                        db.session.commit()
                        flash("Account created. You can log in now.", "ok")
                        return redirect(url_for("login"))
                    except Exception as e:
                        db.session.rollback()
                        msg = ("err", "Registration failed. Please try again.")
        return render_template("register.html", app_name=APP_NAME, flash_msg=msg)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        msg = None
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            pw = request.form.get("password", "")
            
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(pw):
                session["uid"] = user.id
                session["email"] = email
                return redirect(url_for("home"))
            msg = ("err", "Invalid email or password.")
        return render_template("login.html", app_name=APP_NAME, flash_msg=msg)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ---------------------- Routes: password reset ----------------------
    @app.route("/reset", methods=["GET", "POST"])
    def reset_request():
        msg = None
        dev_link = None
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = User.query.filter_by(email=email).first()
            if user:
                token = signer().dumps(email)
                base = os.environ.get("RESET_BASE_URL", request.host_url.rstrip("/"))
                dev_link = f"{base}{url_for('reset_with_token', token=token)}"
                msg = ("ok", "Reset link generated (dev mode).")
            else:
                msg = ("err", "Email not found.")
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
                user = User.query.filter_by(email=email).first()
                if user:
                    user.set_password(pw)
                    db.session.commit()
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

        # Determine seed - use daily seed or generate random for practice
        seed = None
        is_daily = request.args.get("daily") == "1"
        if is_daily:
            seed = today_seed(mode)

        grid, words = make_puzzle(cfg["rows"], cfg["cols"], cfg["words"], seed)
        return render_template("play.html",
                             app_name=APP_NAME, mode=mode, cfg=cfg,
                             grid=grid, words=words, seed=seed or 0,
                             daily=is_daily)

    @app.route("/submit/<mode>", methods=["POST"])
    @login_required
    def submit_score(mode):
        if mode not in MODES:
            return redirect(url_for("home"))

        # Extract score data from form
        elapsed = int(request.form.get("elapsed", "0") or 0)
        score = int(request.form.get("score", "0") or 0)
        seed = request.form.get("seed", "")
        note = (request.form.get("note", "") or "")[:140]

        # Create new score record
        try:
            score_record = Score(
                user_id=session["uid"],
                game_mode=mode,
                points=score,
                time_ms=elapsed * 1000 if elapsed > 0 else 0,  # Convert seconds to milliseconds
                words_found=score,  # For now, using score as words found
                played_at=datetime.datetime.utcnow()
            )
            db.session.add(score_record)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("Error saving score. Please try again.", "error")

        return redirect(url_for("leaderboard"))

    @app.route("/leaderboard")
    @login_required
    def leaderboard():
        leaders = {}
        for mode_name in MODES.keys():
            # Get top 20 scores for this mode
            top_scores = db.session.query(Score, User).join(User).filter(
                Score.game_mode == mode_name
            ).order_by(
                Score.points.desc(),
                Score.time_ms.asc(),
                Score.created_at.asc()
            ).limit(20).all()
            
            leaders[mode_name] = [{
                "score": score.points,
                "elapsed": score.time_ms // 1000 if score.time_ms else None,
                "note": "",
                "created_at": score.created_at,
                "email": user.email
            } for score, user in top_scores]
        
        return render_template("leaderboard.html", app_name=APP_NAME, leaders=leaders)

    @app.route("/daily-leaderboard")
    @login_required
    def daily_leaderboard():
        today = datetime.date.today()
        dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(7)]
        day = request.args.get("day", dates[0])

        leaders = {}
        for mode_name in MODES.keys():
            seed = abs(hash(f"{day}:{mode_name}")) % (10**9)
            # For daily leaderboard, we'd need to track seed in scores table
            # For now, show all scores for the mode from that day
            day_start = datetime.datetime.fromisoformat(day)
            day_end = day_start + datetime.timedelta(days=1)
            
            daily_scores = db.session.query(Score, User).join(User).filter(
                Score.game_mode == mode_name,
                Score.created_at >= day_start,
                Score.created_at < day_end
            ).order_by(
                Score.points.desc(),
                Score.time_ms.asc(),
                Score.created_at.asc()
            ).limit(20).all()
            
            leaders[mode_name] = [{
                "score": score.points,
                "elapsed": score.time_ms // 1000 if score.time_ms else None,
                "note": "",
                "created_at": score.created_at,
                "email": user.email
            } for score, user in daily_scores]

        return render_template("daily_leaderboard.html", app_name=APP_NAME,
                             leaders=leaders, dates=dates, day=day)

    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)