import os, io, logging
from time import time
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, request, jsonify, abort, session, redirect, url_for, flash, send_from_directory, make_response
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import func, text
from models import db, Score, PuzzleBank, User, Post, PostReaction, PostReport, Purchase, CreditTxn
from puzzles import generate_puzzle, MODE_CONFIG
from services.credits import spend_credits, InsufficientCredits, DoubleCharge
from llm_hint import rephrase_hint_or_fallback
from functools import wraps
from csrf_utils import require_csrf, csrf_exempt
from mail_utils import generate_reset_token, verify_reset_token, send_password_reset_email, send_temporary_password_email
import stripe

logger = logging.getLogger(__name__)

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

# Simple in-memory rate limiting for password reset (single process only)
_reset_rate_limit = {}

def throttle_reset(ip: str, limit=5, window_sec=600):
    """Simple rate limiting: 5 requests per 10 minutes per IP"""
    now = time()
    bucket = _reset_rate_limit.get(ip, [])
    # Remove old entries outside the time window
    bucket = [t for t in bucket if now - t < window_sec]

    if len(bucket) >= limit:
        return True  # Rate limited

    bucket.append(now)
    _reset_rate_limit[ip] = bucket
    return False  # Not rate limited

def get_session_user():
    """Get current user from session"""
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

def session_required(f):
    """Custom authentication decorator using centralized auth check"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session, g
        # Centralized authentication check - inline to avoid import issues
        if not (current_user.is_authenticated or session.get('user_id') or getattr(g, 'user', None)):
            return redirect(url_for('core.login'))
        return f(*args, **kwargs)
    return decorated_function

def api_auth_required(f):
    """API-specific authentication decorator that returns JSON errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session, g
        # Centralized authentication check - inline to avoid import issues
        if not (current_user.is_authenticated or session.get('user_id') or getattr(g, 'user', None)):
            return jsonify({"error": "Authentication required"}), 401
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
    # Simple 3-block home page design
    return render_template("home.html")

@bp.get("/play/<mode>")
@session_required
def play(mode):
    if mode not in ("easy", "medium", "hard"): abort(404)
    daily = request.args.get("daily") == "1"
    category = None if daily else _clean_category(request.args.get("category"))

    # Get user stats for display
    user = get_session_user()
    user_stats = {}
    if user:
        # Get free games used (assuming there's a games_played_free field)
        free_games_used = getattr(user, 'games_played_free', 0) or 0
        user_stats = {
            'credits': user.mini_word_credits or 0,
            'free_games_used': free_games_used,
            'free_games_limit': 5  # Default limit
        }

    return render_template("play.html",
                         mode=mode,
                         daily=daily,
                         cfg=MODE_CONFIG[mode],
                         category=category,
                         user_stats=user_stats)

@bp.post("/api/debug/reset-game-counter")
@session_required
def reset_game_counter():
    """Debug endpoint to reset game counter - remove after testing"""
    user = get_session_user()
    if user:
        user.games_played_free = 0
        db.session.commit()
        return jsonify({"ok": True, "message": f"Reset games_played_free to 0 for user {user.id}"})
    return jsonify({"error": "No user found"}), 401

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

    # Track game usage for logged-in users (but only for new games)
    user = get_session_user()
    if user:
        try:
            # Get current free games used
            free_games_used = getattr(user, 'games_played_free', 0) or 0
            FREE_GAMES_LIMIT = 5  # Define the limit

            # Only increment if starting a completely new game (not from reset or refresh)
            is_reset = request.args.get('reset') == '1'
            if puzzle_key not in session and not is_reset:
                if free_games_used < FREE_GAMES_LIMIT:
                    # Free game - increment counter
                    user.games_played_free = free_games_used + 1
                    db.session.commit()
                    logger.info(f"User {user.id} started free game {free_games_used + 1}/{FREE_GAMES_LIMIT}")
                else:
                    # Would be a paid game - but we're not implementing that here yet
                    logger.info(f"User {user.id} would need to pay for game (used {free_games_used}/{FREE_GAMES_LIMIT})")
        except Exception as e:
            logger.error(f"Error tracking game usage for user {user.id}: {e}")
            db.session.rollback()

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
        session[f"{puzzle_key}_seed"] = int(time()) if not daily else int(date.today().strftime("%Y%m%d"))

    try:
        seed = session[f"{puzzle_key}_seed"]
        P = generate_puzzle(mode, seed=seed, category=category)
        P["puzzle_id"] = None
        session[puzzle_key] = P
        session[f"{puzzle_key}_completed"] = False
        return jsonify(P)
    except Exception as e:
        print(f"Puzzle generation error: {e}")
        return jsonify({"error": f"Failed to generate puzzle: {str(e)}"}), 500

@bp.post("/api/score")
@require_csrf
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
@require_csrf
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

    idem = f"hint_unlock:{session_user.id}:{int(time())//5}"
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
@require_csrf
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
    return render_template("terms.html", last_updated="2025-09-16")

@bp.get("/policy")
def policy():
    return render_template("policy.html", last_updated="2025-09-16")

@bp.get("/privacy")
def privacy():
    return render_template("privacy.html")

@bp.route("/game-counters-demo", methods=["GET"])
def game_counters_demo():
    """Demo page for the professional game counter system"""
    return render_template("game-counters-demo.html")

@bp.route("/health", methods=["GET"])
def health():
    """Health check route with config status (no secrets exposed)"""
    from flask import current_app, jsonify
    cfg = current_app.config
    return jsonify({
        "ok": True,
        "provider": cfg.get("MAIL_PROVIDER"),
        "resend": bool(cfg.get("RESEND_API_KEY")),
        "mail_server": bool(cfg.get("MAIL_SERVER") or cfg.get("SMTP_HOST")),
        "mail_username": bool(cfg.get("MAIL_USERNAME") or cfg.get("SMTP_USER")),
        "scheme": cfg.get("PREFERRED_URL_SCHEME"),
        "ttl": cfg.get("PASSWORD_RESET_TOKEN_MAX_AGE"),
        "asset_version": cfg.get("ASSET_VERSION"),
    }), 200

@bp.route("/_test/send_reset_email", methods=["POST"])
def _test_send_reset_email():
    """Dev-only email smoke test (blocked in production)"""
    import os
    from flask import abort, request

    # Hard block in production
    if os.getenv("ENV", "").lower() in ("prod", "production"):
        abort(404)

    from mail_utils import generate_reset_token, send_password_reset_email
    email = (request.form.get("email") or "").strip().lower()
    if not email:
        abort(400)

    token = generate_reset_token(email)
    send_password_reset_email(email, token)
    return ("", 204)

# Guide route
@bp.get("/guide")
def guide():
    return render_template("brand_guide.html")

@bp.get("/faq")
def faq():
    return render_template("faq.html")

# Additional routes for existing templates

@bp.get("/leaderboard")
def leaderboard():
    game_type = request.args.get('game', 'word_search')

    if game_type in ('ttt', 'c4'):
        # Arcade game leaderboard
        return render_template("leaderboard_arcade.html", game_type=game_type)
    else:
        # Original word search leaderboard
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

@bp.get("/daily-challenge")
def daily_challenge():
    """Mixed genre daily challenge - rotates through different categories each day"""
    from datetime import date
    import random

    # Categories to rotate through
    categories = ["animals", "food", "sports", "cars", "home", "colors", "technology"]

    # Use today's date as seed to ensure same category for all players on same day
    today = date.today()
    random.seed(int(today.strftime("%Y%m%d")))
    daily_category = random.choice(categories)

    # Always use medium difficulty for daily challenge
    return redirect(url_for("core.play", mode="medium", daily=1, category=daily_category))

@bp.get("/play/daily-challenge")
def play_daily_challenge():
    """Direct route for daily challenge (alternative URL)"""
    return redirect(url_for("core.daily_challenge"))

@bp.get("/store")
@session_required
def store_page():
    welcome_pack_available = current_user and not current_user.welcome_pack_purchased
    return render_template("brand_store.html", welcome_pack_available=welcome_pack_available)

@bp.get("/api/store/packs")
@session_required
def get_store_packs():
    """API endpoint to get available credit packs for current user"""
    welcome_pack_available = current_user and not current_user.welcome_pack_purchased

    packs = []

    # Add welcome pack if available
    if welcome_pack_available:
        welcome_pack = CREDIT_PACKAGES["welcome"].copy()
        welcome_pack["id"] = "welcome"
        packs.append(welcome_pack)

    # Add other packs
    for pack_id, pack_config in CREDIT_PACKAGES.items():
        if pack_id != "welcome":
            pack = pack_config.copy()
            pack["id"] = pack_id
            packs.append(pack)

    return jsonify({"packs": packs})

# ---------- COMMUNITY: FEED ----------

@bp.get("/community")
@session_required
def community():
    from community_service import CommunityService

    page = max(1, int(request.args.get("page", 1)))
    per = max(5, min(20, int(request.args.get("per", 10))))
    category = request.args.get("category")  # Optional category filter

    # Calculate offset for pagination
    offset = (page - 1) * per

    # Get community feed using enhanced service
    posts = CommunityService.get_community_feed(
        user_id=current_user.id if current_user and current_user.is_authenticated else None,
        category=category,
        limit=per,
        offset=offset
    )

    print(f"DEBUG: Enhanced community page - found {len(posts)} posts on page {page}, category={category}")

    # Get reaction counts and user reactions in bulk for template
    ids = [p.id for p in posts]
    r_counts = {pid: 0 for pid in ids}
    user_reactions = {}

    if ids:
        # Get reaction counts
        rows = db.session.execute(
            text("SELECT post_id, COUNT(*) FROM post_reactions WHERE post_id = ANY(:ids) GROUP BY post_id"),
            {"ids": ids}
        ).all()
        for pid, cnt in rows:
            r_counts[int(pid)] = int(cnt)

        # Get user's reactions if logged in
        if current_user and current_user.is_authenticated:
            try:
                rows = PostReaction.query.filter(
                    PostReaction.post_id.in_(ids),
                    PostReaction.user_id == current_user.id
                ).all()
                user_reactions = {r.post_id: r.reaction_type for r in rows}
            except Exception as e:
                # Transaction may be aborted, need to rollback
                db.session.rollback()

                # Handle missing id column in post_reactions table
                if "does not exist" in str(e) or "aborted" in str(e):
                    user_reactions = {}  # No user reactions available
                    logger.warning(f"Failed to get user reactions: {e}")
                else:
                    user_reactions = {}
                    logger.error(f"Unexpected error getting user reactions: {e}")

    # Check if there are more posts for pagination
    has_more = len(posts) == per

    # Get user's community summary for display
    user_summary = None
    if current_user and current_user.is_authenticated:
        user_summary = CommunityService.get_user_community_summary(current_user.id)

    return render_template(
        "community.html",
        posts=posts,
        has_more=has_more,
        page=page,
        category=category,
        categories=CommunityService.CATEGORIES,
        content_types=CommunityService.CONTENT_TYPES,
        r_counts=r_counts,
        user_reactions=user_reactions,
        user_summary=user_summary
    )

@bp.post("/community/new")
@login_required
@require_csrf
def community_new():
    from community_service import CommunityService

    # Get form data
    body = sanitize_html(request.form.get("body","")).strip()
    category = request.form.get("category", "general")
    content_type = request.form.get("content_type", "general")

    # Handle image upload
    image = request.files.get("image")
    url = None; w=h=None
    if image and image.filename:
        try:
            url, w, h = save_image_file(image, subdir="posts")
        except Exception:
            return jsonify({"ok": False, "error": "bad_image"}), 400

    # Validate input
    if not body and not url:
        return jsonify({"ok": False, "error": "Post content cannot be empty"}), 400
    if len(body) > 500:
        return jsonify({"ok": False, "error": "Post is too long (max 500 characters)"}), 400

    # Create post using enhanced service with proper rate limiting
    post, message = CommunityService.create_post(
        user_id=current_user.id,
        body=body,
        category=category,
        content_type=content_type,
        image_url=url
    )

    if not post:
        # Rate limit or other error
        if "wait" in message.lower():
            return jsonify({"ok": False, "error": message, "cooldown": True}), 429
        else:
            return jsonify({"ok": False, "error": message}), 400

    # Update post with image dimensions if needed
    if url and w and h:
        post.image_width = w
        post.image_height = h
        db.session.commit()

    print(f"DEBUG: Enhanced post created with id={post.id}, category={post.category}, content_type={post.content_type}")
    return jsonify({
        "ok": True,
        "id": post.id,
        "category": post.category,
        "content_type": post.content_type
    })

@bp.post("/community/react/<int:post_id>")
@login_required
@require_csrf
def community_react(post_id):
    """Handle post reactions with proper error handling and transaction safety"""
    from community_service import CommunityService

    # Get reaction type from request
    data = request.get_json() or {}
    reaction_type = data.get('reaction_type', 'love')

    try:
        # Add reaction using enhanced service with proper rate limiting and transaction handling
        reaction, message = CommunityService.add_reaction(
            user_id=current_user.id,
            post_id=post_id,
            reaction_type=reaction_type
        )

        if not reaction:
            # Handle different error types appropriately
            if "rate limit" in message.lower() or "wait" in message.lower():
                return jsonify({"status": "error", "message": message}), 429
            elif "already reacted" in message.lower() or "permanent" in message.lower():
                return jsonify({"status": "already", "message": message}), 200
            elif "not found" in message.lower():
                return jsonify({"status": "error", "message": message}), 404
            elif "invalid" in message.lower():
                return jsonify({"status": "error", "message": message}), 400
            else:
                return jsonify({"status": "error", "message": message}), 500

        # Success case - get updated reaction count
        try:
            total_reactions = db.session.execute(
                text("SELECT COUNT(*) FROM post_reactions WHERE post_id=:pid"), {"pid": post_id}
            ).scalar()
        except Exception as e:
            # If counting fails, log but don't fail the request
            logger.warning(f"Failed to count reactions for post {post_id}: {e}")
            total_reactions = 0

        logger.info(f"User {current_user.id} successfully reacted to post {post_id} with {reaction_type}")

        return jsonify({
            "status": "ok",
            "message": message,
            "user_reacted": True,
            "total_reactions": int(total_reactions),
            "reaction_type": reaction_type
        })

    except Exception as e:
        # Ensure session is clean on any unexpected error
        db.session.rollback()
        logger.error(f"Unexpected error in community_react for user {current_user.id}, post {post_id}: {e}")
        return jsonify({
            "status": "error",
            "message": "Something went wrong. Please try again later."
        }), 500

@bp.post("/community/report/<int:post_id>")
@login_required
@require_csrf
def community_report(post_id):
    from community_service import CommunityService

    reason = (request.json or {}).get("reason", "").strip()[:240]
    if not reason:
        return jsonify({"ok": False, "error": "Please provide a reason for reporting"}), 400

    # Report post using enhanced service with proper rate limiting
    report, message = CommunityService.report_post(
        user_id=current_user.id,
        post_id=post_id,
        reason=reason
    )

    if not report:
        if "limit" in message.lower():
            return jsonify({"ok": False, "error": message}), 429
        else:
            return jsonify({"ok": False, "error": message}), 400

    return jsonify({"ok": True, "message": "Report submitted successfully"})

@bp.delete("/community/delete/<int:post_id>")
@login_required
@require_csrf
def community_delete_post(post_id):
    from community_service import CommunityService

    try:
        # Check if post exists and belongs to current user
        post = db.session.get(Post, post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        if post.user_id != current_user.id:
            return jsonify({"error": "You can only delete your own posts"}), 403

        # Delete the post using community service
        success = CommunityService.delete_post(post_id, current_user.id)

        if success:
            return jsonify({"ok": True, "message": "Post deleted successfully"})
        else:
            return jsonify({"error": "Failed to delete post"}), 500

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting post {post_id} for user {current_user.id}: {e}")
        return jsonify({"error": "Something went wrong. Please try again later."}), 500

@bp.post("/community/mute")
@login_required
@require_csrf
def community_mute():
    from community_service import CommunityService

    data = request.get_json() or {}
    muted_user_id = data.get("user_id")
    reason = data.get("reason", "").strip()[:100]

    if not muted_user_id:
        return jsonify({"ok": False, "error": "User ID required"}), 400

    if muted_user_id == current_user.id:
        return jsonify({"ok": False, "error": "Cannot mute yourself"}), 400

    # Mute user using enhanced service
    mute, message = CommunityService.mute_user(
        muter_user_id=current_user.id,
        muted_user_id=muted_user_id,
        reason=reason
    )

    if not mute:
        return jsonify({"ok": False, "error": message}), 400

    return jsonify({"ok": True, "message": "User muted successfully"})

@bp.get("/community/stats")
@login_required
def community_stats():
    from community_service import CommunityService

    # Get user's community activity summary
    summary = CommunityService.get_user_community_summary(current_user.id)
    return jsonify({"ok": True, "stats": summary})

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
        user = db.session.get(User, user_id)
        if not user:
            abort(404)

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

        # Get recent scores (use raw SQL to handle missing columns)
        try:
            from sqlalchemy import text
            from datetime import datetime
            # Rollback any failed transaction first
            try:
                db.session.rollback()
            except:
                pass

            # Use only columns that definitely exist
            result = db.session.execute(text("""
                SELECT id, user_id, mode, points, words_found, time_ms,
                       COALESCE(played_at, created_at) as display_date,
                       game_mode, created_at
                FROM scores
                WHERE user_id = :user_id
                ORDER BY COALESCE(played_at, created_at) DESC
                LIMIT 10
            """), {"user_id": user.id})

            # Convert to objects with the needed attributes
            recent_scores = []
            for row in result:
                # Ensure display_date is a datetime object
                display_date = row.display_date
                if isinstance(display_date, str):
                    try:
                        display_date = datetime.fromisoformat(display_date.replace('Z', '+00:00'))
                    except:
                        display_date = row.created_at or datetime.utcnow()

                # Create a simple object with the attributes the template expects
                score_obj = type('Score', (), {
                    'id': row.id,
                    'user_id': row.user_id,
                    'mode': row.mode,
                    'game_mode': row.game_mode,
                    'points': row.points or 0,
                    'words_found': row.words_found or 0,
                    'time_ms': row.time_ms,
                    'played_at': display_date,
                    'created_at': row.created_at
                })()
                recent_scores.append(score_obj)

        except Exception as e:
            print(f"Error getting recent scores: {e}")
            # Make sure to rollback failed transaction
            try:
                db.session.rollback()
            except:
                pass
            recent_scores = []

        return render_template("profile.html", user=user, best_scores=best_scores, recent_scores=recent_scores)

    except Exception as e:
        print(f"Error in profile_view: {e}")
        import traceback
        traceback.print_exc()
        flash("Profile not found or error loading profile", "error")
        return redirect("/")

@bp.get("/me")
def profile_me():
    from flask import session, g
    # Centralized authentication check - inline to avoid import issues
    if not (current_user.is_authenticated or session.get('user_id') or getattr(g, 'user', None)):
        return redirect(url_for('core.login'))

    # Try Flask-Login first, then session
    if current_user.is_authenticated:
        user_id = current_user.get_id()
    else:
        user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('core.login'))

    return redirect(url_for("core.profile_view", user_id=user_id))

@bp.get("/profile")
def profile():
    from flask import session, g
    # Centralized authentication check - inline to avoid import issues
    if not (current_user.is_authenticated or session.get('user_id') or getattr(g, 'user', None)):
        return redirect(url_for('core.login'))

    # Try Flask-Login first, then session
    if current_user.is_authenticated:
        user_id = current_user.get_id()
    else:
        user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('core.login'))

    return redirect(url_for("core.profile_view", user_id=user_id))

@bp.post("/profile/avatar")
@login_required
@require_csrf
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

# Legacy game route removed to avoid conflict with arcade blueprint /game prefix
# Arcade games are now at /game/tictactoe and /game/connect4
# Word search games are at /play/<mode>

@bp.post("/api/dev/reset-cooldowns")
@require_csrf
def api_dev_reset_cooldowns():
    """Development endpoint to reset cooldown timers"""
    if not session.get('user_id'):
        return jsonify({"error": "Please log in"}), 401

    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in"}), 401

    try:
        # Reset both cooldown timestamps
        session_user.profile_image_updated_at = None
        session_user.display_name_updated_at = None
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Both cooldown timers reset successfully!",
            "image_cooldown": "CLEARED",
            "name_cooldown": "CLEARED"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to reset cooldowns: {str(e)}"}), 500

@bp.post("/api/dev/clear-broken-image")
@require_csrf
def api_dev_clear_broken_image():
    """Clear broken profile image URL and reset cooldown"""
    if not session.get('user_id'):
        return jsonify({"error": "Please log in"}), 401

    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in"}), 401

    try:
        # Clear the broken profile image URL and reset cooldown
        session_user.profile_image_url = None
        session_user.profile_image_updated_at = None
        try:
            session_user.display_name_updated_at = None
        except AttributeError:
            # Column doesn't exist in some environments, skip it
            pass

        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Broken profile image cleared and cooldown reset",
            "old_url": "Cleared"
        })

    except Exception as e:
        print(f"Error clearing broken image: {e}")
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Authentication routes
@bp.route("/login", methods=["GET", "POST", "HEAD"])
@csrf_exempt
def login():
    # If user is already authenticated, redirect to home
    if session.get('user_id') or get_session_user():
        print(f"[DEBUG] User already authenticated, redirecting to home")
        return redirect("/")

    if request.method in ["GET", "HEAD"]:
        resp = make_response(render_template("login.html"))
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return resp

    email = request.form.get("email")
    password = request.form.get("password")

    print(f"[DEBUG] Login attempt for email: {email}")

    if not email or not password:
        flash("Email and password are required", "error")
        return render_template("login.html")

    user = User.query.filter_by(email=email).first()
    print(f"[DEBUG] User found: {user is not None}")

    if not user:
        print(f"[DEBUG] No user found with email: {email}")
        flash("Invalid email or password", "error")
        return render_template("login.html")

    password_check = user.check_password(password)
    print(f"[DEBUG] Password check result for {email}: {password_check}")

    if not password_check:
        print(f"[DEBUG] Login failed for {email} - password check failed")
        flash("Invalid email or password", "error")
        return render_template("login.html")

    print(f"[DEBUG] Login successful for {email}, redirecting to home")
    login_user(user, remember=True)
    # Do NOT clear the entire session – it wipes Flask-Login state and other data
    # If you want a clean slate, selectively pop what you don't need:
    for k in ("csrf_token_temp",):  # example of keys you might want to drop
        session.pop(k, None)

    session["user_id"] = user.id
    session["is_admin"] = bool(user.is_admin)
    session.permanent = True  # Use PERMANENT_SESSION_LIFETIME for rolling sessions
    session["last_activity"] = int(time())  # Initialize activity tracking

    # Generate fresh CSRF token on login
    from csrf_utils import rotate_csrf_token
    rotate_csrf_token()
    session.modified = True
    print(f"[DEBUG] Session setup complete, user_id: {user.id}")
    return redirect("/")

@bp.route("/register", methods=["GET", "POST", "HEAD"])
@csrf_exempt
def register():
    if request.method in ["GET", "HEAD"]:
        return render_template("register.html", hide_everything_except_content=True)

    username = request.form.get("username", "").strip()
    display_name = request.form.get("display_name", "").strip() or username
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    agree_terms = request.form.get("agree_terms")

    # Basic validation
    if not agree_terms:
        flash("You must agree to the Terms of Service and Privacy Policy", "error")
        return render_template("register.html", hide_everything_except_content=True)
    if not username or len(username) < 3:
        flash("Username must be at least 3 characters", "error")
        return render_template("register.html", hide_everything_except_content=True)

    if not email or "@" not in email:
        flash("Valid email address required", "error")
        return render_template("register.html", hide_everything_except_content=True)

    if not password or len(password) < 6:
        flash("Password must be at least 6 characters", "error")
        return render_template("register.html", hide_everything_except_content=True)

    # Check for existing users
    if User.query.filter_by(username=username).first():
        flash("Username already taken", "error")
        return render_template("register.html", hide_everything_except_content=True)

    if User.query.filter_by(email=email).first():
        flash("Email already registered", "error")
        return render_template("register.html", hide_everything_except_content=True)

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

        login_user(user, remember=True)
        session.clear()
        session["user_id"] = user.id
        session["is_admin"] = bool(user.is_admin)
        session.permanent = True  # Use PERMANENT_SESSION_LIFETIME for rolling sessions
        session["last_activity"] = int(time())  # Initialize activity tracking

        # Generate fresh CSRF token on registration/login
        from csrf_utils import rotate_csrf_token
        rotate_csrf_token()
        return redirect("/")

    except Exception as e:
        db.session.rollback()
        flash(f"Registration failed: {str(e)}", "error")
        return render_template("register.html")

@bp.route("/reset", methods=["GET", "POST", "HEAD"])
@csrf_exempt
def reset_request():
    """Password reset request route"""
    if request.method in ["GET", "HEAD"]:
        return render_template("reset_request.html", hide_everything_except_content=True)

    # Rate limiting check
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if throttle_reset(ip):
        flash("Too many reset requests. Try again later", "error")
        return redirect(url_for('core.login'))

    email = request.form.get("email", "").strip().lower()

    if not email or "@" not in email:
        flash("Valid email address required", "error")
        return render_template("reset_request.html", hide_everything_except_content=True)

    # Don't reveal if email exists - security best practice
    # Always show the same success message regardless of whether user exists
    try:
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate a temporary password
            import secrets
            import string
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

            # Update user's password
            user.set_password(temp_password)
            db.session.commit()

            # Send temporary password via email
            print(f"DEBUG: Generated temporary password for {email}: {temp_password}")
            email_sent = send_temporary_password_email(email, temp_password)

            if email_sent:
                flash("A temporary password has been sent to your email address", "success")
            else:
                # Email failed - show password on page as fallback
                flash(f"Email delivery failed. Your temporary password is: {temp_password}", "success")

        return redirect(url_for('core.login'))

    except Exception as e:
        print(f"Password reset error: {e}")
        flash("Something went wrong. Please try again", "error")
        return render_template("reset_request.html", hide_everything_except_content=True)

@bp.route("/reset/<token>", methods=["GET", "POST", "HEAD"])
@csrf_exempt
def reset_token(token):
    """Password reset with token route"""
    from flask import current_app

    print(f"[DEBUG] Reset token accessed: {token[:8]}...")

    # Verify token on all requests
    email = verify_reset_token(token, current_app.config.get("PASSWORD_RESET_TOKEN_MAX_AGE", 3600))
    print(f"[DEBUG] Token verification result - email: {email}")

    if not email:
        print(f"[DEBUG] Token verification failed, redirecting to reset_request")
        flash("Reset link is invalid or expired", "error")
        return redirect(url_for('core.reset_request'))

    if request.method in ["GET", "HEAD"]:
        print(f"[DEBUG] Rendering reset token form for email: {email}")
        return render_template("reset_token.html", token=token, hide_everything_except_content=True)

    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not password or len(password) < 6:
        flash("Password must be at least 6 characters", "error")
        return render_template("reset_token.html", token=token, hide_everything_except_content=True)

    if password != confirm_password:
        flash("Passwords don't match", "error")
        return render_template("reset_token.html", token=token, hide_everything_except_content=True)

    try:
        # Find user by email from token
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Invalid or expired reset link", "error")
            return redirect(url_for('core.reset_request'))

        # Try to update user password
        try:
            user.set_password(password)
            db.session.commit()
            flash("Password updated successfully. You can now sign in", "success")
            return redirect(url_for('core.login'))

        except Exception as password_error:
            print(f"[DEBUG] Failed to set user password: {password_error}")
            db.session.rollback()

            # Generate temporary password and email it
            import secrets
            import string
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            print(f"[DEBUG] Generated temporary password: {temp_password}")

            try:
                user.set_password(temp_password)
                db.session.commit()
                print(f"[DEBUG] Temporary password saved to database for user: {email}")

                # Send temporary password email
                send_temporary_password_email(email, temp_password)
                print(f"[DEBUG] Temporary password email sent to: {email}")

                flash("There was an issue with your password. A temporary password has been sent to your email. You can change it in your profile after logging in.", "warning")
                return redirect(url_for('core.login'))

            except Exception as temp_error:
                print(f"Failed to set temporary password: {temp_error}")
                db.session.rollback()
                flash("Password reset failed. Please try again or contact support.", "error")
                return render_template("reset_token.html", token=token, hide_everything_except_content=True)

    except Exception as e:
        print(f"Password reset token error: {e}")
        db.session.rollback()
        flash("Invalid or expired reset link", "error")
        return render_template("reset_token.html", token=token, hide_everything_except_content=True)

@bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    """Clean logout - clear session and redirect"""
    from flask import current_app as app

    username = getattr(current_user, 'username', None)
    uid = getattr(current_user, 'id', None)
    print(f"[LOGOUT] User {username} (ID: {uid}) logging out")

    prior_keys = list(session.keys())
    logout_user()           # flask-login: clears remember, user id
    session.clear()         # belt & suspenders

    resp = make_response(redirect(url_for('core.login')))
    # Explicitly drop cookies
    session_cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
    resp.delete_cookie(session_cookie_name, path="/")
    remember_cookie = app.config.get("REMEMBER_COOKIE_NAME", "remember_token")
    resp.delete_cookie(remember_cookie, path="/")

    print(f"[LOGOUT] Session cleared successfully; removed keys: {prior_keys}")
    print(f"[LOGOUT] Still authenticated after logout: {getattr(current_user,'is_authenticated', False)}")
    return resp




@bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    """Keep session alive with heartbeat"""
    if session.get('user_id'):
        session.permanent = True  # Refresh session timeout
    return "", 204  # No content response




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
@bp.post("/api/profile/change-password")
@login_required
@require_csrf
def api_profile_change_password():
    """Change user's password"""
    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in"}), 401

    try:
        data = request.get_json()
        current_password = data.get("current_password", "").strip()
        new_password = data.get("new_password", "").strip()

        if not current_password or not new_password:
            return jsonify({"error": "Current password and new password are required"}), 400

        # Verify current password
        if not session_user.check_password(current_password):
            return jsonify({"error": "Current password is incorrect"}), 400

        # Validate new password
        if len(new_password) < 8:
            return jsonify({"error": "New password must be at least 8 characters long"}), 400

        # Update password
        session_user.set_password(new_password)
        db.session.commit()

        return jsonify({"success": True, "message": "Password changed successfully"})

    except Exception as e:
        print(f"Error in api_profile_change_password: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to change password"}), 500


@bp.post("/api/profile/change-name")
@login_required
@require_csrf
def api_profile_change_name():
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
        if session_user.display_name_updated_at:
            last_update = session_user.display_name_updated_at
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
@require_csrf
def api_profile_set_image():
    """Upload and set user profile image using the new base64 image manager"""
    # Check authentication for API endpoint
    if not session.get('user_id'):
        return jsonify({"error": "Please log in to upload images"}), 401

    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in to upload images"}), 401

    try:
        from datetime import datetime, timedelta
        from image_manager import image_manager

        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Check 24-hour cooldown first
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
                return jsonify({
                    "error": f"Please wait {hours}h {minutes}m before changing image again",
                    "cooldown": True,
                    "remaining_seconds": int(remaining.total_seconds())
                }), 429

        # Use the new image manager for upload and processing
        result = image_manager.upload_profile_image(session_user.id, file)

        if result['success']:
            # Update the cooldown timestamp
            session_user.profile_image_updated_at = datetime.utcnow()
            db.session.commit()

            return jsonify({
                "success": True,
                "message": result['message'],
                "format": result.get('format', 'unknown'),
                "size": result.get('size', 0)
            })
        else:
            return jsonify({"error": result['error']}), 400

    except Exception as e:
        print(f"Error in api_profile_set_image: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@bp.get("/api/profile-image/<int:user_id>")
def serve_profile_image(user_id):
    """Serve user's profile image with fallback to default avatar"""
    try:
        from image_manager import image_manager
        from flask import Response

        # Get image data from the image manager
        image_bytes, mime_type = image_manager.serve_profile_image(user_id)

        if image_bytes:
            return Response(image_bytes, mimetype=mime_type)
        else:
            # Fallback to default avatar - return empty response so template shows default
            return '', 404

    except Exception as e:
        print(f"Error serving profile image for user {user_id}: {e}")
        return '', 500

@bp.delete("/api/profile/delete-image")
@require_csrf
def api_profile_delete_image():
    """Delete user's profile image"""
    # Check authentication for API endpoint
    if not session.get('user_id'):
        return jsonify({"error": "Please log in"}), 401

    session_user = get_session_user()
    if not session_user:
        return jsonify({"error": "Please log in"}), 401

    try:
        from image_manager import image_manager

        # Delete using image manager
        result = image_manager.delete_profile_image(session_user.id)

        if result['success']:
            # Also clear cooldown
            session_user.profile_image_updated_at = None
            db.session.commit()

            return jsonify({
                "success": True,
                "message": result['message']
            })
        else:
            return jsonify({"error": result['error']}), 400

    except Exception as e:
        print(f"Error in api_profile_delete_image: {e}")
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# ---------- STRIPE PAYMENT INTEGRATION ----------

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_CONFIGURED = bool(stripe.api_key)

# Credit packages configuration with environment variable support
CREDIT_PACKAGES = {
    "welcome": {
        "credits": 100,
        "price_cents": 99,
        "name": "Welcome Pack",
        "one_time_only": True,
        "price_env": "STORE_PRICE_WELCOME",
        "badge": "First-time offer"
    },
    "starter": {
        "credits": 500,
        "price_cents": 499,
        "name": "Starter Credits",
        "price_env": "STORE_PRICE_STARTER",
        "badge": "Great starter"
    },
    "plus": {
        "credits": 1200,
        "price_cents": 999,
        "name": "Plus Credits",
        "price_env": "STORE_PRICE_PLUS",
        "badge": "Best value"
    },
    "mega": {
        "credits": 2600,
        "price_cents": 1999,
        "name": "Mega Credits",
        "price_env": "STORE_PRICE_MEGA",
        "badge": "Power user"
    }
}

def get_stripe_price_id(package):
    """Get Stripe price ID from environment variable or fallback to inline price creation"""
    price_env = package.get("price_env")
    if price_env:
        price_id = os.getenv(price_env)
        if price_id:
            return price_id, None  # Return price_id and None for price_data

    # Fallback to inline price creation if env var not set
    price_data = {
        'currency': 'usd',
        'product_data': {
            'name': package["name"],
            'description': f'{package["credits"]} credits for Mini Word Finder'
        },
        'unit_amount': package["price_cents"],
    }
    return None, price_data

@bp.post("/purchase/create-session")
@require_csrf
def create_checkout_session():
    # Check authentication for API endpoint (support both session and Flask-Login)
    session_user = get_session_user()
    if not session_user and (not current_user or not current_user.is_authenticated):
        return jsonify({"error": "Please log in to make a purchase"}), 401

    # Use session user if available, fallback to current_user
    user = session_user or current_user

    try:
        # Check if Stripe is configured
        if not STRIPE_CONFIGURED:
            return jsonify({"error": "Payment system not configured. Please contact support."}), 503

        data = request.get_json()
        package_key = data.get("package")

        if package_key not in CREDIT_PACKAGES:
            return jsonify({"error": "Invalid package"}), 400

        package = CREDIT_PACKAGES[package_key]

        # Check if this is a one-time only package and if user has already purchased it
        if package.get("one_time_only") and package_key == "welcome":
            if user.welcome_pack_purchased:
                return jsonify({"error": "Welcome Pack can only be purchased once"}), 400

        # Create purchase record
        purchase = Purchase(
            user_id=user.id,
            package_key=package_key,
            credits=package["credits"],
            amount_cents=package["price_cents"],
            currency="usd",
            status="created"
        )
        db.session.add(purchase)
        db.session.flush()  # Get the ID

        # Get Stripe price configuration
        price_id, price_data = get_stripe_price_id(package)

        # Create line item based on whether we have a price ID or need inline price data
        if price_id:
            line_item = {
                'price': price_id,
                'quantity': 1,
            }
        else:
            line_item = {
                'price_data': price_data,
                'quantity': 1,
            }

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[line_item],
            mode='payment',
            locale='en',
            success_url=url_for('core.payment_success', session_id='{CHECKOUT_SESSION_ID}', _external=True),
            cancel_url=url_for('core.store_page', _external=True),
            metadata={
                'purchase_id': purchase.id,
                'user_id': user.id,
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
                # Atomic transaction to prevent race conditions
                try:
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
                    if not user:
                        raise ValueError("User not found")

                    user.mini_word_credits = (user.mini_word_credits or 0) + purchase.credits

                    # Mark welcome pack as purchased if this was the welcome pack
                    if purchase.package_key == "welcome":
                        # Double-check welcome pack hasn't been used (extra safety)
                        if user.welcome_pack_purchased:
                            raise ValueError("Welcome pack already purchased by this user")
                        user.welcome_pack_purchased = True

                    db.session.commit()

                    flash(f"Successfully purchased {purchase.credits} credits!", "success")
                    return redirect("/wallet")

                except Exception as e:
                    db.session.rollback()
                    print(f"Error processing payment: {e}")
                    flash("Payment processing error. Please contact support.", "error")
                    return redirect(url_for('core.store_page'))

            elif purchase and purchase.status == "completed":
                flash("Payment already processed successfully", "info")
                return redirect("/wallet")
            else:
                flash("Payment record not found or invalid", "error")
        else:
            flash("Payment was not completed", "error")

    except stripe.error.StripeError as e:
        flash(f"Payment verification failed: {str(e)}", "error")
    except Exception as e:
        flash(f"Error processing payment: {str(e)}", "error")

    return redirect(url_for('core.store_page'))

@bp.post("/stripe/webhook")
@csrf_exempt
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

# Missing Game API Endpoints

@bp.post("/api/game/progress/save")
@api_auth_required
@csrf_exempt
def save_game_progress():
    """Save game progress for authenticated users"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        user = get_session_user()
        if not user:
            return jsonify({"error": "Not authenticated"}), 401

        # For now, just return success since localStorage fallback works
        # TODO: Implement actual database storage if needed
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error saving game progress: {e}")
        return jsonify({"error": "Save failed"}), 500

@bp.get("/api/game/progress/load")
@api_auth_required
def load_game_progress():
    """Load game progress for authenticated users"""
    try:
        mode = request.args.get("mode", "easy")
        daily = request.args.get("daily") == "1"

        user = get_session_user()
        if not user:
            return jsonify({"ok": False, "error": "Not authenticated"}), 401

        # For now, return empty since we're relying on localStorage
        # This prevents the "not found" error and lets localStorage handle it
        return jsonify({"ok": False, "message": "No progress found"})

    except Exception as e:
        print(f"Error loading game progress: {e}")
        return jsonify({"ok": False, "error": "Load failed"}), 500

@bp.post("/api/game/progress/clear")
@api_auth_required
def clear_game_progress():
    """Clear game progress for authenticated users"""
    try:
        mode = request.args.get("mode", "easy")
        daily = request.args.get("daily") == "1"

        user = get_session_user()
        if not user:
            return jsonify({"ok": False, "error": "Not authenticated"}), 401

        # For now, just return success since localStorage handles clearing
        return jsonify({"ok": True})

    except Exception as e:
        print(f"Error clearing game progress: {e}")
        return jsonify({"ok": False, "error": "Clear failed"}), 500

@bp.get("/api/word/lesson")
@csrf_exempt
def get_word_lesson():
    """Get word lesson/definition for auto-teach feature"""
    try:
        word = request.args.get('word', '').upper()
        if not word:
            return jsonify({"error": "No word provided"}), 400

        # Simple word definitions for common programming/game words
        definitions = {
            "FLASK": "A lightweight Python web framework for building web applications",
            "ROUTE": "A URL pattern that maps to a specific function in web applications",
            "LOOP": "A programming construct that repeats code until a condition is met",
            "EAGLE": "A large bird of prey with keen eyesight and powerful wings",
            "PLANET": "A celestial body that orbits around a star",
            "PYTHON": "A high-level programming language known for its simplicity",
            "CODE": "Instructions written in a programming language",
            "GAME": "An interactive form of entertainment with rules and objectives"
        }

        definition = definitions.get(word, f"A word found in the puzzle: {word}")

        return jsonify({
            "word": word,
            "definition": definition,
            "pronunciation": f"/{word.lower()}/"
        })
    except Exception as e:
        print(f"Error getting word lesson: {e}")
        return jsonify({"error": "Lesson not found"}), 404

@bp.post("/api/game/reveal")
@api_auth_required
@csrf_exempt
def reveal_word():
    """Reveal a word in the current puzzle for credits"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        puzzle_id = data.get('puzzle_id')
        word_id = data.get('word_id')

        if not puzzle_id or not word_id:
            return jsonify({"error": "Missing puzzle_id or word_id"}), 400

        # In a real implementation, you would:
        # 1. Deduct credits from user
        # 2. Get the word path from puzzle data
        # 3. Return the word path and lesson data

        # For now, return a mock response that will work with the frontend
        user = get_session_user()
        if not user:
            return jsonify({"error": "User not authenticated"}), 401

        # Get the actual word path from the current puzzle
        word_path = []

        # Get puzzle data from session
        puzzle_data = None
        for key in session:
            if key.startswith('puzzle_') and not session.get(f"{key}_completed", False):
                puzzle_data = session[key]
                break

        if puzzle_data and puzzle_data.get('grid'):
            # Find the actual word position in the grid
            word_path = find_word_in_grid(puzzle_data['grid'], word_id)
            if not word_path:
                # If word not found, return error
                return jsonify({"error": f"Word '{word_id}' not found in current puzzle"}), 400

        # Deduct credits (simplified)
        if user.mini_word_credits and user.mini_word_credits >= 5:
            user.mini_word_credits -= 5
            db.session.commit()

        return jsonify({
            "ok": True,
            "balance": user.mini_word_credits or 0,
            "path": word_path,
            "lesson": {
                "word": word_id.upper(),
                "definition": f"Definition for {word_id.upper()}",
                "pronunciation": f"/{word_id.lower()}/"
            }
        })

    except Exception as e:
        print(f"Error in reveal_word: {e}")
        return jsonify({"error": "Reveal failed"}), 500

# Game API Endpoints for Arcade Games (Connect 4, Tic-tac-toe, Word Game)

@bp.post("/game/api/start")
@session_required
@csrf_exempt
def start_game():
    """Start a game session and track free play usage"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        game_type = data.get('game')  # 'c4', 'ttt', 'wordgame'
        if not game_type:
            return jsonify({"error": "Game type required"}), 400

        user = get_session_user()
        if not user:
            return jsonify({"error": "User not authenticated"}), 401

        # Check if we need to reset daily counters
        from datetime import date
        today = date.today()

        # Reset counters if it's a new day
        if not hasattr(user, 'last_free_reset_date') or user.last_free_reset_date != today:
            user.wordgame_played_free = 0
            user.connect4_played_free = 0
            user.tictactoe_played_free = 0
            user.last_free_reset_date = today
            db.session.commit()

        # Get current free play count for this game
        free_column_map = {
            'c4': 'connect4_played_free',
            'ttt': 'tictactoe_played_free',
            'wordgame': 'wordgame_played_free'
        }

        column_name = free_column_map.get(game_type)
        if not column_name:
            return jsonify({"error": "Invalid game type"}), 400

        current_free_plays = getattr(user, column_name, 0)
        FREE_PLAYS_LIMIT = 5

        # Check if user can play for free
        if current_free_plays < FREE_PLAYS_LIMIT:
            # Free play
            setattr(user, column_name, current_free_plays + 1)
            db.session.commit()

            return jsonify({
                "ok": True,
                "charged": 0,
                "free_remaining": FREE_PLAYS_LIMIT - (current_free_plays + 1),
                "credits": user.mini_word_credits or 0
            })
        else:
            # Check if user has enough credits (5 credits per game)
            GAME_COST = 5
            if not user.mini_word_credits or user.mini_word_credits < GAME_COST:
                return jsonify({
                    "ok": False,
                    "error": "insufficient_credits"
                }), 400

            # Charge credits
            user.mini_word_credits -= GAME_COST
            db.session.commit()

            return jsonify({
                "ok": True,
                "charged": GAME_COST,
                "free_remaining": 0,
                "credits": user.mini_word_credits
            })

    except Exception as e:
        print(f"Error in start_game: {e}")
        return jsonify({"error": "Failed to start game"}), 500

@bp.post("/game/api/result")
@session_required
@csrf_exempt
def report_game_result():
    """Report game result for statistics"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        game_type = data.get('game')
        won = data.get('won', False)

        # For now, just return success
        # TODO: Implement game statistics tracking if needed

        return jsonify({"ok": True})

    except Exception as e:
        print(f"Error in report_game_result: {e}")
        return jsonify({"error": "Failed to report result"}), 500


@bp.get("/game/api/status")
@csrf_exempt
def get_game_status():
    """Get current game counter status for authenticated users"""
    try:
        user = get_session_user()
        if not user:
            # Return default values for unauthenticated users
            return jsonify({
                "ok": True,
                "wordgame_free_remaining": 0,
                "connect4_free_remaining": 0,
                "tictactoe_free_remaining": 0,
                "credits": 0
            })

        # Check if we need to reset daily counters
        from datetime import date
        today = date.today()

        # Reset counters if it's a new day
        if not hasattr(user, 'last_free_reset_date') or user.last_free_reset_date != today:
            user.wordgame_played_free = 0
            user.connect4_played_free = 0
            user.tictactoe_played_free = 0
            user.last_free_reset_date = today
            db.session.commit()

        # Calculate remaining free plays
        wordgame_remaining = max(0, 5 - (user.wordgame_played_free or 0))
        connect4_remaining = max(0, 5 - (user.connect4_played_free or 0))
        tictactoe_remaining = max(0, 5 - (user.tictactoe_played_free or 0))

        return jsonify({
            "ok": True,
            "wordgame_free_remaining": wordgame_remaining,
            "connect4_free_remaining": connect4_remaining,
            "tictactoe_free_remaining": tictactoe_remaining,
            "credits": user.mini_word_credits or 0
        })

    except Exception as e:
        print(f"Error in get_game_status: {e}")
        return jsonify({"error": "Failed to get status"}), 500