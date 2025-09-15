import os, secrets, time, io
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, request, jsonify, abort, session, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import func, text
from models import db, Score, PuzzleBank, User, Post, PostReaction, PostReport, Purchase, CreditTxn
from puzzles import generate_puzzle, MODE_CONFIG
from services.credits import spend_credits, InsufficientCredits, DoubleCharge
from llm_hint import rephrase_hint_or_fallback
from functools import wraps
import stripe

def get_session_user():
    """Get current user from session"""
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

def session_required(f):
    """Custom authentication decorator that checks session directly"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('core.login'))
        return f(*args, **kwargs)
    return decorated_function

# Image upload dependencies
try:
    from PIL import Image
    import bleach
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

bp = Blueprint("core", __name__)

HINT_COST = int(os.getenv("HINT_CREDIT_COST", "1"))

# Image upload configuration
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024      # 10 MB
MAX_DIM = 2048                          # max width/height after resize
AVATAR_COST = int(os.getenv("CREDIT_COST_PROFILE_IMAGE", "1"))

BLEACH_TAGS = ["b","i","strong","em","u","br","p","ul","ol","li","code"]
BLEACH_ATTRS = {}
BLEACH_PROTOCOLS = ["http","https"]

def sanitize_html(text: str) -> str:
    if not PIL_AVAILABLE:
        return (text or "").strip()[:1000]  # Simple fallback
    return bleach.clean(text or "", tags=BLEACH_TAGS, attributes=BLEACH_ATTRS,
                        protocols=BLEACH_PROTOCOLS, strip=True)

def _ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def save_image_file(fs, subdir="uploads"):
    """
    Validates and stores an uploaded image. Returns (url, w, h).
    Local storage version; swap with S3/Supabase as needed.
    """
    if not PIL_AVAILABLE:
        raise ValueError("image_processing_unavailable")

    if not fs or not fs.filename:
        return None
    mime = fs.mimetype or ""
    if mime not in ALLOWED_IMAGE_MIME:
        raise ValueError("unsupported_image_type")
    fs.stream.seek(0, io.SEEK_END)
    size = fs.stream.tell()
    if size > MAX_IMAGE_BYTES:
        raise ValueError("image_too_large")
    fs.stream.seek(0)

    img = Image.open(fs.stream).convert("RGBA")
    w, h = img.size
    scale = min(1.0, MAX_DIM / max(w, h)) if max(w, h) > MAX_DIM else 1.0
    if scale < 1.0:
        img = img.resize((int(w*scale), int(h*scale)), Image.Resampling.LANCZOS)
        w, h = img.size

    # Convert to WEBP for size (keeps alpha; browsers fine)
    filename = f"{secrets.token_hex(10)}.webp"
    local_dir = os.path.join("static", subdir)
    _ensure_dir(local_dir)
    path = os.path.join(local_dir, filename)
    img.save(path, format="WEBP", method=6, quality=85)

    url = f"/static/{subdir}/{filename}"
    return url, w, h
HINTS_MAX = int(os.getenv("HINTS_PER_PUZZLE", "3"))
HINT_TTL = int(os.getenv("HINT_UNLOCK_TTL_SEC", "120"))
HINT_COOLDOWN = int(os.getenv("HINT_COOLDOWN_SEC", "2"))

DIR_NAMES = {
    "E": ("east", "→"), "S": ("south", "↓"), "W": ("west", "←"), "N": ("north", "↑"),
    "SE": ("southeast", "↘"), "NE": ("northeast", "↗"), "SW": ("southwest", "↙"), "NW": ("northwest", "↖")
}

def _clean_category(val):
    if not val: return None
    return "".join(ch for ch in val.lower() if ch.isalnum() or ch in "_-") or None

@bp.route("/", methods=["GET", "POST"])
def index():
    # If user is logged in, show game interface
    if current_user and current_user.is_authenticated:
        return render_template("index.html")
    elif session.get('user_id'):
        return render_template("index.html")
    else:
        # If not logged in, show login page directly
        return render_template("login.html")

@bp.get("/play/<mode>")
@session_required
def play(mode):
    if mode not in ("easy", "medium", "hard"): abort(404)
    daily = request.args.get("daily") == "1"
    category = None if daily else _clean_category(request.args.get("category"))
    return render_template("play.html", mode=mode, daily=daily, cfg=MODE_CONFIG[mode], category=category)

@bp.get("/api/puzzle")
def api_puzzle():
    mode = request.args.get("mode", "easy")
    daily = request.args.get("daily") == "1"
    category = None if daily else _clean_category(request.args.get("category"))
    if mode not in ("easy", "medium", "hard"): abort(400, "bad mode")

    # Create a unique session key for this puzzle configuration
    puzzle_key = f"puzzle_{mode}_{daily}_{category or 'none'}"

    # Check if we already have this puzzle in session and it's not completed
    if puzzle_key in session and not session.get(f"{puzzle_key}_completed", False):
        return jsonify(session[puzzle_key])

    # 1) daily scheduled template?
    if daily:
        pb = PuzzleBank.query.filter_by(active=True, mode=mode, daily_date=date.today()).first()
        if pb:
            puzzle_data = {
                "grid": pb.grid, "words": pb.words, "mode": mode,
                "time_limit": pb.time_limit, "seed": pb.seed, "puzzle_id": pb.id
            }
            session[puzzle_key] = puzzle_data
            session[f"{puzzle_key}_completed"] = False
            return jsonify(puzzle_data)

    # 2) random active template, filtered by category if provided
    query = PuzzleBank.query.filter(
        PuzzleBank.active.is_(True),
        PuzzleBank.mode == mode,
    )
    if category:
        query = query.filter(PuzzleBank.category == category)
    else:
        query = query.filter(PuzzleBank.category.is_(None))

    pb = query.order_by(func.random()).first()

    if pb:
        puzzle_data = {
            "grid": pb.grid, "words": pb.words, "mode": mode,
            "time_limit": pb.time_limit, "seed": pb.seed, "puzzle_id": pb.id
        }
        session[puzzle_key] = puzzle_data
        session[f"{puzzle_key}_completed"] = False
        return jsonify(puzzle_data)

    # 3) fallback procedural - use consistent seed for session
    if f"{puzzle_key}_seed" not in session:
        session[f"{puzzle_key}_seed"] = int(time.time()) if not daily else int(date.today().strftime("%Y%m%d"))

    seed = session[f"{puzzle_key}_seed"]
    P = generate_puzzle(mode, seed=seed, category=category)
    P["puzzle_id"] = None
    session[puzzle_key] = P
    session[f"{puzzle_key}_completed"] = False
    return jsonify(P)

@bp.post("/api/score")
def api_score():
    if not session.get('user_id'):
        return jsonify({"error": "Please log in"}), 401

    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in"}), 401
    p = request.get_json(force=True)
    s = Score(
        user_id=session_user.id,
        mode=p.get("mode"),
        total_words=int(p.get("total_words", 0)),
        found_count=int(p.get("found_count", 0)),
        duration_sec=int(p.get("duration_sec", 0)),
        completed=bool(p.get("completed")),
        seed=p.get("seed"),
        category=p.get("category"),
        hints_used=int(p.get("hints_used", 0)),
        puzzle_id=p.get("puzzle_id"),
        created_at=datetime.utcnow(),
    )
    db.session.add(s)
    db.session.commit()

    # Mark puzzle as completed in session so a new one can be generated
    mode = p.get("mode")
    daily = p.get("daily", False)
    category = p.get("category")
    puzzle_key = f"puzzle_{mode}_{daily}_{category or 'none'}"
    session[f"{puzzle_key}_completed"] = True

    # record that user has seen this template
    if s.puzzle_id:
        db.session.execute(
            "INSERT INTO puzzle_plays(user_id,puzzle_id,played_at) VALUES (:u,:p,:t) ON CONFLICT DO NOTHING",
            {"u": session_user.id, "p": s.puzzle_id, "t": datetime.utcnow()}
        )
        db.session.commit()
    return jsonify({"ok": True, "score_id": s.id})

def _hint_state(): return session.get("hint_unlock") or {}
def _set_hint_state(d): session["hint_unlock"] = d

@bp.post("/api/hint/unlock")
def api_hint_unlock():
    if not session.get('user_id'):
        return jsonify({"error": "Please log in"}), 401

    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in"}), 401
    used = int((request.json or {}).get("used", 0))
    if used >= HINTS_MAX:
        return jsonify({"ok": False, "error": "max_hints"}), 400

    st = _hint_state()
    last = st.get("last_at")
    if last and (datetime.utcnow() - datetime.fromisoformat(last)).total_seconds() < HINT_COOLDOWN:
        return jsonify({"ok": False, "error": "cooldown"}), 429

    idem = f"hint_unlock:{session_user.id}:{int(time.time())//5}"
    try:
        with spend_credits(session_user, HINT_COST, "hint_unlock", idem=idem):
            token = secrets.token_hex(8)
            _set_hint_state({
                "token": token,
                "expires_at": (datetime.utcnow() + timedelta(seconds=HINT_TTL)).isoformat(),
                "consumed": False,
                "charged": HINT_COST,
                "refunded": False,
                "last_at": datetime.utcnow().isoformat(),
            })
            return jsonify({"ok": True, "token": token, "balance": session_user.mini_word_credits, "ttl_sec": HINT_TTL})
    except InsufficientCredits:
        return jsonify({"ok": False, "error": "insufficient"}), 402
    except DoubleCharge:
        return jsonify({"ok": False, "error": "cooldown"}), 429

@bp.post("/api/hint/ask")
def api_hint_ask():
    if not session.get('user_id'):
        return jsonify({"error": "Please log in"}), 401

    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in"}), 401
    from puzzles import generate_puzzle
    p = request.get_json(force=True)
    token = p.get("token") or ""
    mode = p.get("mode") or "easy"
    category = p.get("category")
    seed = p.get("seed")
    puzzle_id = p.get("puzzle_id")
    term = (p.get("term") or "").strip().upper()

    st = _hint_state()
    if not st or st.get("consumed") or st.get("token") != token:
        return jsonify({"ok": False, "error": "locked"}), 403
    exp = datetime.fromisoformat(st["expires_at"])
    if datetime.utcnow() > exp:
        _set_hint_state(st | {"consumed": False})
        return jsonify({"ok": False, "error": "expired"}), 410

    hit = None
    if puzzle_id:
        pb = PuzzleBank.query.get(puzzle_id)
        if not pb or not pb.active:
            st["consumed"] = True
            _set_hint_state(st)
            return jsonify({"ok": False, "error": "template_missing_refunded"}), 500
        if term not in set(pb.words or []):
            return jsonify({"ok": False, "error": "not_in_puzzle"}), 400
        hit = (pb.answers or {}).get(term)
        if not hit:
            # rebuild key on the fly if answers missing
            from puzzles import _build_key
            hit = _build_key(pb.grid, [term]).get(term)
    else:
        if mode not in ("easy", "medium", "hard"): abort(400, "bad mode")
        P = generate_puzzle(mode, seed=seed, category=category)
        if term not in set(P["words"]):
            return jsonify({"ok": False, "error": "not_in_puzzle"}), 400
        hit = P["answers"].get(term)

    if not hit:
        # refund & relock
        st["consumed"] = True
        st["refunded"] = True
        _set_hint_state(st)
        return jsonify({"ok": False, "error": "not_found_refunded"}), 500

    r1, c1 = hit["start"][0] + 1, hit["start"][1] + 1
    name, arrow = DIR_NAMES.get(hit["dir"], ("", ""))
    text = rephrase_hint_or_fallback(term, r1, c1, name, arrow, hit["len"])
    guidance = {
        "word": term,
        "start": {"row": r1, "col": c1},
        "direction": name,
        "arrow": arrow,
        "length": hit["len"],
        "instruction": text
    }
    st["consumed"] = True
    _set_hint_state(st)
    session["hints_used_run"] = int(session.get("hints_used_run", 0)) + 1
    return jsonify({"ok": True, "guidance": guidance})

# Terms and Privacy Policy routes
@bp.get("/terms")
def terms():
    return render_template("terms.html")

@bp.get("/privacy")
def privacy():
    return render_template("privacy.html")

# Additional routes for existing templates

@bp.get("/leaderboard")
def leaderboard():
    top_scores = Score.query.order_by(Score.points.desc()).limit(50).all()
    return render_template("leaderboard.html", scores=top_scores)

@bp.get("/daily_leaderboard")
def daily_leaderboard():
    from datetime import date
    today = date.today()
    daily_scores = Score.query.filter(
        func.date(Score.created_at) == today
    ).order_by(Score.points.desc()).limit(50).all()
    return render_template("daily_leaderboard.html", scores=daily_scores, date=today)

@bp.get("/store")
@session_required
def store_page():
    return render_template("store.html")

# ---------- COMMUNITY: FEED ----------

@bp.get("/community")
@session_required
def community():
    page = max(1, int(request.args.get("page", 1)))
    per = max(5, min(20, int(request.args.get("per", 10))))
    q = Post.query.filter_by(is_hidden=False).order_by(Post.created_at.desc())
    items = q.paginate(page=page, per_page=per, error_out=False)
    # reaction counts in bulk
    ids = [p.id for p in items.items]
    r_counts = {pid: 0 for pid in ids}
    if ids:
        rows = db.session.execute(
            text("SELECT post_id, COUNT(*) FROM post_reactions WHERE post_id = ANY(:ids) GROUP BY post_id"),
            {"ids": ids}
        ).all()
        for pid, cnt in rows: r_counts[int(pid)] = int(cnt)
    # which posts current_user reacted to
    reacted = set()
    if ids:
        rows = PostReaction.query.filter(PostReaction.post_id.in_(ids),
                                         PostReaction.user_id==current_user.id).all()
        reacted = {r.post_id for r in rows}
    return render_template("community.html", items=items, r_counts=r_counts, reacted=reacted)

@bp.post("/community/new")
@login_required
def community_new():
    body = sanitize_html(request.form.get("body","")).strip()
    image = request.files.get("image")
    url = None; w=h=None
    if image and image.filename:
        try:
            url, w, h = save_image_file(image, subdir="posts")
        except Exception:
            return jsonify({"ok": False, "error": "bad_image"}), 400
    if not body and not url:
        return jsonify({"ok": False, "error": "empty"}), 400
    p = Post(user_id=current_user.id, body=body, image_url=url, image_width=w, image_height=h)
    db.session.add(p); db.session.commit()
    return jsonify({"ok": True, "id": p.id})

@bp.post("/community/react/<int:post_id>")
@login_required
def community_react(post_id):
    post = Post.query.get_or_404(post_id)
    if post.is_hidden: return jsonify({"ok": False, "error": "hidden"}), 400
    existing = PostReaction.query.get((post_id, current_user.id))
    if existing:
        db.session.delete(existing); db.session.commit()
        reacted=False
    else:
        db.session.add(PostReaction(post_id=post_id, user_id=current_user.id))
        db.session.commit()
        reacted=True
    cnt = db.session.execute(
        text("SELECT COUNT(*) FROM post_reactions WHERE post_id=:pid"), {"pid": post_id}
    ).scalar_one()
    return jsonify({"ok": True, "reacted": reacted, "count": int(cnt)})

@bp.post("/community/report/<int:post_id>")
@login_required
def community_report(post_id):
    reason = (request.json or {}).get("reason","").strip()[:240]
    if not Post.query.get(post_id):
        return jsonify({"ok": False, "error": "not_found"}), 404
    db.session.add(PostReport(post_id=post_id, user_id=current_user.id, reason=reason or None))
    db.session.commit()
    return jsonify({"ok": True})

@bp.get("/wallet")
@session_required
def wallet_page():
    try:
        # Get recent transactions
        recent_transactions = CreditTxn.query.filter_by(user_id=current_user.id).order_by(CreditTxn.created_at.desc()).limit(10).all()

        # Get recent purchases
        recent_purchases = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.created_at.desc()).limit(5).all()

        return render_template("wallet.html", transactions=recent_transactions, purchases=recent_purchases)
    except Exception as e:
        print(f"Error in wallet_page: {e}")
        import traceback
        traceback.print_exc()
        return render_template("wallet.html", transactions=[], purchases=[])

# ---------- PROFILE: VIEW + AVATAR CHANGE (credit-gated) ----------

@bp.get("/u/<int:user_id>")
def profile_view(user_id):
    try:
        user = User.query.get_or_404(user_id)

        # Get best scores by mode
        try:
            best_scores = db.session.query(
                Score.mode,
                func.max(Score.points).label('best_points'),
                func.count(Score.id).label('games_count')
            ).filter_by(user_id=user.id).group_by(Score.mode).all()
        except Exception as e:
            print(f"Error getting best scores: {e}")
            best_scores = []

        # Get recent scores
        try:
            recent_scores = Score.query.filter_by(user_id=user.id).order_by(Score.played_at.desc()).limit(10).all()
        except Exception as e:
            print(f"Error getting recent scores: {e}")
            recent_scores = []

        return render_template("profile.html", user=user, best_scores=best_scores, recent_scores=recent_scores)

    except Exception as e:
        print(f"Error in profile_view: {e}")
        import traceback
        traceback.print_exc()
        flash("Profile not found or error loading profile", "error")
        return redirect("/")

@bp.get("/me")
@session_required
def profile_me():
    user = get_session_user()
    return redirect(url_for("core.profile_view", user_id=user.id))

@bp.get("/profile")
@session_required
def profile():
    user = get_session_user()
    return redirect(url_for("core.profile_view", user_id=user.id))

@bp.post("/profile/avatar")
@login_required
def profile_avatar():
    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify({"ok": False, "error": "no_image"}), 400
    # spend credits for avatar change
    try:
        with spend_credits(current_user, AVATAR_COST, "avatar_change", idem=f"avatar:{current_user.id}:{file.filename}"):
            try:
                url, w, h = save_image_file(file, subdir="avatars")
            except Exception:
                raise ValueError("bad_image")
            current_user.profile_image_url = url
            current_user.profile_image_updated_at = datetime.utcnow()
            db.session.commit()
    except InsufficientCredits:
        return jsonify({"ok": False, "error": "insufficient"}), 402
    except Exception:
        # spend_credits auto-refunds on exception
        return jsonify({"ok": False, "error": "bad_image"}), 400

    return jsonify({"ok": True, "url": current_user.profile_image_url, "balance": current_user.mini_word_credits})

@bp.get("/game/<mode>")
@login_required
def game_legacy(mode):
    """Legacy game route - redirect to new play route"""
    return redirect(f"/play/{mode}")

# Authentication routes
@bp.route("/login", methods=["GET", "POST", "HEAD"])
def login():
    if request.method in ["GET", "HEAD"]:
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        flash("Invalid email or password", "error")
        return render_template("login.html")

    login_user(user)
    session.clear()
    session["user_id"] = user.id
    session["is_admin"] = bool(user.is_admin)
    session.permanent = True  # Use the PERMANENT_SESSION_LIFETIME (30 days)
    return redirect("/")

@bp.route("/register", methods=["GET", "POST", "HEAD"])
def register():
    if request.method in ["GET", "HEAD"]:
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    display_name = request.form.get("display_name", "").strip() or username
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    agree_terms = request.form.get("agree_terms")

    # Basic validation
    if not agree_terms:
        flash("You must agree to the Terms of Service and Privacy Policy", "error")
        return render_template("register.html")
    if not username or len(username) < 3:
        flash("Username must be at least 3 characters", "error")
        return render_template("register.html")

    if not email or "@" not in email:
        flash("Valid email address required", "error")
        return render_template("register.html")

    if not password or len(password) < 6:
        flash("Password must be at least 6 characters", "error")
        return render_template("register.html")

    # Check for existing users
    if User.query.filter_by(username=username).first():
        flash("Username already taken", "error")
        return render_template("register.html")

    if User.query.filter_by(email=email).first():
        flash("Email already registered", "error")
        return render_template("register.html")

    try:
        user = User(
            username=username,
            display_name=display_name,
            email=email,
            mini_word_credits=10  # Starting credits
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        session.clear()
        session["user_id"] = user.id
        session["is_admin"] = bool(user.is_admin)
        session.permanent = True  # Use the PERMANENT_SESSION_LIFETIME (30 days)
        return redirect("/")

    except Exception as e:
        db.session.rollback()
        flash(f"Registration failed: {str(e)}", "error")
        return render_template("register.html")

@bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Logout route - clear session and redirect"""
    try:
        user_id = session.get('user_id')
        username = getattr(current_user, 'username', 'Unknown') if current_user and current_user.is_authenticated else 'Anonymous'

        print(f"[LOGOUT] User {username} (ID: {user_id}) logging out")

        # Clear Flask-Login session
        logout_user()
        # Clear session data
        session.clear()

        print("[LOGOUT] Session cleared successfully")
        return redirect("/login")

    except Exception as e:
        print(f"[LOGOUT] Error during logout: {e}")
        # Force clear session even if error
        try:
            logout_user()
        except:
            pass
        session.clear()
        return redirect("/login")

@bp.post("/api/logout")
def api_logout():
    """API logout endpoint"""
    try:
        user_id = session.get('user_id')
        username = getattr(current_user, 'username', 'Unknown') if current_user and current_user.is_authenticated else 'Anonymous'

        print(f"[API_LOGOUT] User {username} (ID: {user_id}) logging out via API")

        logout_user()
        session.clear()

        print("[API_LOGOUT] Session cleared successfully")
        return jsonify({"ok": True})
    except Exception as e:
        print(f"[API_LOGOUT] Error during logout: {e}")
        try:
            logout_user()
        except:
            pass
        session.clear()
        return jsonify({"ok": False, "error": "Logout failed"}), 500

@bp.route("/clear-session")
def clear_session():
    """Clear puzzle sessions for testing"""
    session.clear()
    return redirect("/")

@bp.route("/clear-cars")
def clear_cars():
    """Clear cars puzzle specifically"""
    # Clear ALL possible cars puzzle sessions
    keys_to_remove = []
    for key in session.keys():
        if "cars" in key or "puzzle_easy_False" in key:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del session[key]

    print(f"DEBUG CLEAR: Removed session keys: {keys_to_remove}")
    return redirect("/play/easy?category=cars")

@bp.route("/clear-category/<category>")
def clear_category(category):
    """Clear specific category puzzle"""
    keys_to_remove = []
    for key in session.keys():
        if category in key or f"puzzle_easy_False_{category}" == key:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del session[key]

    print(f"DEBUG CLEAR: Removed {category} session keys: {keys_to_remove}")
    return redirect(f"/play/easy?category={category}")

@bp.route("/debug-session")
def debug_session():
    """Show current session contents"""
    return jsonify(dict(session))

@bp.route("/debug-puzzle")
def debug_puzzle():
    """Debug puzzle generation"""
    from puzzles import generate_puzzle, CATEGORY_WORDS
    mode = request.args.get("mode", "easy")
    category = request.args.get("category", "cars")

    # Show what we have
    available_categories = list(CATEGORY_WORDS.keys())

    # Force regenerate without session
    P = generate_puzzle(mode, seed=12345, category=category)

    return jsonify({
        "requested_category": category,
        "available_categories": available_categories,
        "has_category": category in CATEGORY_WORDS,
        "generated_words": P["words"],
        "mode": mode
    })

# Legacy routes for backward compatibility

# Profile API routes
@bp.post("/api/profile/change-name")
def api_profile_change_name():
    if not session.get('user_id'):
        return jsonify({"error": "Please log in"}), 401

    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in"}), 401
    try:
        from datetime import datetime, timedelta

        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        new_name = (data.get("name") or "").strip()

        if not new_name or len(new_name) < 1:
            return jsonify({"error": "Display name cannot be empty"}), 400

        if len(new_name) > 50:
            return jsonify({"error": "Display name too long (max 50 characters)"}), 400

        # Check 24-hour cooldown for display name changes
        display_name_updated_at = getattr(session_user, 'display_name_updated_at', None)
        if display_name_updated_at:
            last_update = display_name_updated_at
            # Ensure both datetimes are timezone-naive
            if hasattr(last_update, 'tzinfo') and last_update.tzinfo is not None:
                last_update = last_update.replace(tzinfo=None)

            now = datetime.utcnow()
            if now - last_update < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_update)
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                seconds = int(remaining.total_seconds() % 60)
                return jsonify({
                    "error": f"Please wait {hours}h {minutes}m {seconds}s before changing name again",
                    "cooldown": True,
                    "remaining_seconds": int(remaining.total_seconds())
                }), 429

        session_user.display_name = new_name
        # Only set timestamp if column exists (for backwards compatibility)
        if hasattr(session_user, 'display_name_updated_at'):
            session_user.display_name_updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "new_name": new_name})

    except Exception as e:
        print(f"Error in api_profile_change_name: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@bp.post("/api/profile/set-image")
def api_profile_set_image():
    # Check authentication for API endpoint
    if not session.get('user_id'):
        return jsonify({"error": "Please log in to upload images"}), 401

    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in to upload images"}), 401
    try:
        from datetime import datetime, timedelta
        import os
        from werkzeug.utils import secure_filename

        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Check file size (10MB limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)     # Reset to beginning

        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({"error": "File too large (max 10MB)"}), 400

        # Check file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4'}
        filename = secure_filename(file.filename)
        if not filename or '.' not in filename:
            return jsonify({"error": "Invalid filename"}), 400

        file_ext = filename.rsplit('.', 1)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({"error": "Invalid file type (PNG, JPG, JPEG, GIF, WebP, MP4 only)"}), 400

        # Check MP4 video duration (max 11 seconds)
        if file_ext == 'mp4':
            try:
                import subprocess
                import tempfile

                # Save temp file to check duration
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                    file.seek(0)
                    temp_file.write(file.read())
                    temp_file.flush()

                    # Use ffprobe to get video duration
                    result = subprocess.run([
                        'ffprobe', '-v', 'quiet', '-show_entries',
                        'format=duration', '-of', 'csv=p=0', temp_file.name
                    ], capture_output=True, text=True, timeout=10)

                    if result.returncode != 0:
                        return jsonify({"error": "Invalid MP4 file"}), 400

                    duration = float(result.stdout.strip())
                    if duration > 11.0:
                        return jsonify({"error": "MP4 video too long (max 11 seconds)"}), 400

                # Clean up temp file
                import os
                os.unlink(temp_file.name)
                file.seek(0)  # Reset file pointer

            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError, FileNotFoundError):
                # Skip MP4 validation if ffprobe not available, just allow the upload
                pass
            except Exception as e:
                return jsonify({"error": f"Error processing MP4: {str(e)}"}), 400

        # Check 24-hour cooldown
        if session_user.profile_image_updated_at:
            last_update = session_user.profile_image_updated_at
            # Ensure both datetimes are timezone-naive
            if hasattr(last_update, 'tzinfo') and last_update.tzinfo is not None:
                last_update = last_update.replace(tzinfo=None)

            now = datetime.utcnow()
            if now - last_update < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_update)
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                return jsonify({"error": f"Please wait {hours}h {minutes}m before changing image again"}), 429

        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename with user ID
        unique_filename = f"{session_user.id}_{int(datetime.utcnow().timestamp())}_{filename}"
        file_path = os.path.join(upload_dir, unique_filename)

        # Save the file
        file.seek(0)  # Reset file pointer
        file.save(file_path)

        # Update user's profile image URL and timestamp
        session_user.profile_image_url = f"/static/uploads/{unique_filename}"
        session_user.profile_image_updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "image_url": session_user.profile_image_url})

    except Exception as e:
        print(f"Error in api_profile_set_image: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# ---------- STRIPE PAYMENT INTEGRATION ----------

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_CONFIGURED = bool(stripe.api_key)

# Credit packages configuration
CREDIT_PACKAGES = {
    "starter": {"credits": 500, "price_cents": 499, "name": "Starter Credits"},
    "plus": {"credits": 1200, "price_cents": 999, "name": "Plus Credits"},
    "mega": {"credits": 2600, "price_cents": 1999, "name": "Mega Credits"}
}

@bp.post("/purchase/create-session")
def create_checkout_session():
    # Check authentication for API endpoint
    if not current_user or not current_user.is_authenticated:
        return jsonify({"error": "Please log in to make a purchase"}), 401

    try:
        # Check if Stripe is configured
        if not STRIPE_CONFIGURED:
            return jsonify({"error": "Payment system not configured. Please contact support."}), 503

        data = request.get_json()
        package_key = data.get("package")

        if package_key not in CREDIT_PACKAGES:
            return jsonify({"error": "Invalid package"}), 400

        package = CREDIT_PACKAGES[package_key]

        # Create purchase record
        purchase = Purchase(
            user_id=current_user.id,
            package_key=package_key,
            credits=package["credits"],
            amount_cents=package["price_cents"],
            currency="usd",
            status="created"
        )
        db.session.add(purchase)
        db.session.flush()  # Get the ID

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': package["name"],
                        'description': f'{package["credits"]} credits for Mini Word Finder'
                    },
                    'unit_amount': package["price_cents"],
                },
                'quantity': 1,
            }],
            mode='payment',
            locale='en',
            success_url=url_for('core.payment_success', session_id='{CHECKOUT_SESSION_ID}', _external=True),
            cancel_url=url_for('core.store_page', _external=True),
            metadata={
                'purchase_id': purchase.id,
                'user_id': current_user.id,
                'credits': package["credits"]
            }
        )

        # Update purchase with Stripe session ID
        purchase.stripe_session_id = checkout_session.id
        db.session.commit()

        return jsonify({"checkout_url": checkout_session.url})

    except stripe.error.StripeError as e:
        db.session.rollback()
        print(f"Stripe error: {e}")
        return jsonify({"error": f"Payment error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        print(f"Server error in create_checkout_session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@bp.get("/payment/success")
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash("Invalid payment session", "error")
        return redirect(url_for('core.store_page'))

    try:
        # Retrieve the session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)

        if checkout_session.payment_status == 'paid':
            # Find the purchase record
            purchase = Purchase.query.filter_by(stripe_session_id=session_id).first()

            if purchase and purchase.status == "created":
                # Update purchase status
                purchase.status = "completed"

                # Add credits to user account
                credit_txn = CreditTxn(
                    user_id=purchase.user_id,
                    amount_delta=purchase.credits,
                    reason=f"Purchase: {purchase.package_key}",
                    ref_txn_id=purchase.id
                )
                db.session.add(credit_txn)

                # Update user's credit balance
                user = User.query.get(purchase.user_id)
                user.mini_word_credits = (user.mini_word_credits or 0) + purchase.credits

                db.session.commit()

                flash(f"Successfully purchased {purchase.credits} credits!", "success")
                return redirect("/wallet")
            else:
                flash("Payment already processed or invalid", "error")
        else:
            flash("Payment was not completed", "error")

    except stripe.error.StripeError as e:
        flash(f"Payment verification failed: {str(e)}", "error")
    except Exception as e:
        flash(f"Error processing payment: {str(e)}", "error")

    return redirect(url_for('core.store_page'))

@bp.post("/stripe/webhook")
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        # Invalid payload
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return "Invalid signature", 400

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Find the purchase record
        purchase = Purchase.query.filter_by(stripe_session_id=session['id']).first()

        if purchase and purchase.status == "created":
            # Update purchase status
            purchase.status = "completed"

            # Add credits to user account
            credit_txn = CreditTxn(
                user_id=purchase.user_id,
                amount_delta=purchase.credits,
                reason=f"Purchase: {purchase.package_key}",
                ref_txn_id=purchase.id
            )
            db.session.add(credit_txn)

            # Update user's credit balance
            user = User.query.get(purchase.user_id)
            user.mini_word_credits = (user.mini_word_credits or 0) + purchase.credits

            db.session.commit()

    return "OK", 200