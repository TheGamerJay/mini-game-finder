import os, secrets, datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import text, desc, func
import hashlib

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

    # --- API: Users & Scores for Mini Word Finder ---

    def _hash_ip(ip: str | None) -> str | None:
        if not ip:
            return None
        salt = os.getenv("IP_HASH_SALT", "change-me")
        return hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()

    @app.post("/api/users")
    def create_or_get_user():
        """
        Create a minimal user or fetch one if it already exists.
        Accepts JSON:
          { "username": "jaay", "email": "jaay@example.com", "password": "optional" }
        - You may send username OR email (or both). If either exists, we return that user.
        - If password provided, it will be hashed.
        Returns: { id, username, email, created_at }
        """
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip() or None
        email = (data.get("email") or "").strip().lower() or None
        password = data.get("password")

        if not username and not email:
            return jsonify({"error": "username or email is required"}), 400

        # Try to find existing by email first, else username
        user = None
        if email:
            user = User.query.filter_by(email=email).first()
        if not user and username:
            user = User.query.filter_by(username=username).first()

        if not user:
            user = User(username=username, email=email)
            if password:
                user.set_password(password)
            db.session.add(user)
            db.session.commit()
        else:
            # Optionally update password if newly supplied
            if password:
                user.set_password(password)
                db.session.commit()

        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None
        })

    @app.post("/api/scores")
    def submit_score_api():
        """
        Submit a score.
        JSON body:
        {
          "user_id": 123,                 # required
          "game_mode": "classic",         # optional (default mini_word_finder)
          "points": 150,                  # optional (default 0)
          "time_ms": 92000,               # optional (default 0)
          "words_found": 18,              # optional (default 0)
          "max_streak": 6,                # optional (default 0),
          "device": "desktop"             # optional
        }
        Uses hashed IP (with IP_HASH_SALT) for light anti-abuse signals.
        """
        data = request.get_json(silent=True) or {}

        try:
            user_id = int(data.get("user_id", 0))
        except Exception:
            user_id = 0

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "user not found"}), 404

        game_mode  = (data.get("game_mode") or "mini_word_finder").strip()
        points     = int(data.get("points") or 0)
        time_ms    = int(data.get("time_ms") or 0)
        words_found= int(data.get("words_found") or 0)
        max_streak = int(data.get("max_streak") or 0)
        device     = (data.get("device") or "").strip() or None

        # Basic sanity clamps
        points      = max(points, 0)
        time_ms     = max(time_ms, 0)
        words_found = max(words_found, 0)
        max_streak  = max(max_streak, 0)

        # Hash IP
        real_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ip_hash = _hash_ip((real_ip or "").split(",")[0].strip())

        s = Score(
            user_id=user.id,
            game_mode=game_mode,
            points=points,
            time_ms=time_ms,
            words_found=words_found,
            max_streak=max_streak,
            device=device,
            ip_hash=ip_hash,
        )
        db.session.add(s)
        db.session.commit()

        return jsonify({
            "ok": True,
            "score": {
                "id": s.id,
                "user_id": s.user_id,
                "game_mode": s.game_mode,
                "points": s.points,
                "time_ms": s.time_ms,
                "words_found": s.words_found,
                "max_streak": s.max_streak,
                "played_at": s.played_at.isoformat() if s.played_at else None,
                "device": s.device
            }
        }), 201

    @app.get("/api/leaderboard")
    def leaderboard_api():
        """
        Query params:
          mode: game mode filter (default mini_word_finder)
          period: one of [all, day, week, month]  (default: all)
          limit: max rows (default 25, max 200)

        Returns top scores (highest points) with username/email fallback.
        """
        mode = request.args.get("mode", "mini_word_finder").strip()
        period = request.args.get("period", "all").strip().lower()
        try:
            limit = min(int(request.args.get("limit", 25)), 200)
        except Exception:
            limit = 25

        q = Score.query.filter(Score.game_mode == mode)

        # Period filter
        if period in ("day", "week", "month"):
            if period == "day":
                cutoff_sql = func.now() - func.cast("1 day", db.Interval)   # works on PG
            elif period == "week":
                cutoff_sql = func.now() - func.cast("7 days", db.Interval)
            else:  # month ~ 30 days
                cutoff_sql = func.now() - func.cast("30 days", db.Interval)
            q = q.filter(Score.played_at >= cutoff_sql)

        q = q.order_by(desc(Score.points), Score.time_ms.asc(), desc(Score.max_streak))
        rows = q.limit(limit).all()

        # Map user_id -> display
        user_ids = list({r.user_id for r in rows})
        user_map = {}
        if user_ids:
            for u in User.query.filter(User.id.in_(user_ids)).all():
                user_map[u.id] = u.username or (u.email.split("@")[0] if u.email else f"user_{u.id}")

        return jsonify({
            "mode": mode,
            "period": period,
            "count": len(rows),
            "entries": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "user": user_map.get(r.user_id, f"user_{r.user_id}"),
                    "points": r.points,
                    "time_ms": r.time_ms,
                    "words_found": r.words_found,
                    "max_streak": r.max_streak,
                    "played_at": r.played_at.isoformat() if r.played_at else None
                } for r in rows
            ]
        })

    @app.get("/api/users/<int:user_id>/scores")
    def user_scores_api(user_id: int):
        """
        Return a user's recent scores (newest first).
        Query params:
          limit: max rows (default 50, max 200)
        """
        try:
            limit = min(int(request.args.get("limit", 50)), 200)
        except Exception:
            limit = 50

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "user not found"}), 404

        rows = (
            Score.query.filter_by(user_id=user_id)
            .order_by(desc(Score.played_at), desc(Score.id))
            .limit(limit)
            .all()
        )

        return jsonify({
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "count": len(rows),
            "scores": [
                {
                    "id": r.id,
                    "game_mode": r.game_mode,
                    "points": r.points,
                    "time_ms": r.time_ms,
                    "words_found": r.words_found,
                    "max_streak": r.max_streak,
                    "played_at": r.played_at.isoformat() if r.played_at else None,
                    "device": r.device
                } for r in rows
            ]
        })

    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)