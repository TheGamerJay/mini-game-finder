import os, secrets, datetime
from functools import wraps
import click
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort, render_template_string
)
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import text, desc, func
import hashlib

# Set up constants first
APP_NAME = os.environ.get("APP_NAME", "Mini Word Finder")
SECRET_KEY = os.environ.get("FLASK_SECRET", os.environ.get("SECRET_KEY", secrets.token_hex(32)))

# Import database and models
from models import db, User, Score, PasswordReset, Purchase, CreditTxn
import json, uuid
# puzzle generator (make sure puzzles.py exists)
from puzzles import make_puzzle
import smtplib
from email.message import EmailMessage
from hashlib import sha256
from datetime import timedelta, timezone, datetime

# Game modes (board size / words / timer seconds: 0 = no timer) 
MODES = {
    "easy": {"rows": 10, "cols": 10, "words": 5, "seconds": 0},
    "medium": {"rows": 12, "cols": 12, "words": 7, "seconds": 120},
    "hard": {"rows": 14, "cols": 14, "words": 10, "seconds": 180},
}

def _abs_url(path: str) -> str:
    # Prefer request.url_root when in a request, else APP_BASE_URL
    try:
        base = (request.url_root or "").rstrip("/")
    except RuntimeError:
        base = ""
    if not base:
        base = app.config["APP_BASE_URL"].rstrip("/")
    return base + path

def _send_email(to_email: str, subject: str, text_body: str) -> bool:
    # Dev-friendly: echo to logs instead of sending
    if app.config["DEV_MAIL_ECHO"]:
        app.logger.info(f"[MAIL to {to_email}] {subject}\n{text_body}")
        return True
    host = app.config["SMTP_HOST"]
    if not host:
        app.logger.warning("SMTP not configured; falling back to DEV_MAIL_ECHO")
        app.logger.info(f"[MAIL to {to_email}] {subject}\n{text_body}")
        return True
    msg = EmailMessage()
    msg["From"] = app.config["MAIL_FROM"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)
    try:
        with smtplib.SMTP(host, app.config["SMTP_PORT"], timeout=15) as s:
            if app.config["SMTP_USE_TLS"]:
                s.starttls()
            if app.config["SMTP_USER"]:
                s.login(app.config["SMTP_USER"], app.config["SMTP_PASS"])
            s.send_message(msg)
        return True
    except Exception as e:
        app.logger.error(f"SMTP send failed: {e}")
        return False

def _create_reset_token(u: User) -> str:
    """Create a single-use reset token (store only its hash). Returns the raw token string."""
    # Optionally invalidate old unused tokens for this user:
    PasswordReset.query.filter(
        PasswordReset.user_id == u.id,
        PasswordReset.used == False
    ).update({PasswordReset.used: True})
    token = secrets.token_urlsafe(32)
    pr = PasswordReset(
        user_id=u.id,
        token_hash=sha256(token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=app.config["RESET_TOKEN_TTL_MIN"]),
        used=False,
    )
    db.session.add(pr)
    db.session.commit()
    return token

def _find_valid_reset(token: str) -> tuple[PasswordReset | None, User | None, str | None]:
    """Validate token; returns (reset_row, user, error_message)."""
    th = sha256(token.encode("utf-8")).hexdigest()
    pr = PasswordReset.query.filter_by(token_hash=th).first()
    if not pr:
        return None, None, "Invalid or expired link."
    if pr.used:
        return None, None, "This link has already been used."
    if pr.expires_at < datetime.now(timezone.utc):
        return None, None, "This link has expired."
    u = User.query.get(pr.user_id)
    if not u:
        return None, None, "Account not found."
    return pr, u, None

def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # Core config
    app.config.setdefault("SECRET_KEY", os.getenv("SECRET_KEY", os.urandom(24)))
    app.config.setdefault("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)  # 5 MB
    app.config.setdefault("ALLOWED_IMAGE_EXTENSIONS", {"jpg","jpeg","png","webp"})
    app.config.setdefault("UPLOADS_DIR", os.path.join(app.root_path, "static", "uploads"))
    app.config.setdefault("STORAGE_BACKEND", os.getenv("STORAGE_BACKEND", "local").lower())
    
    # Game config
    app.config.setdefault("STARTING_MINI_WORD_CREDITS", int(os.getenv("STARTING_MINI_WORD_CREDITS", "10")))
    app.config.setdefault("CREDIT_COST_PROFILE_IMAGE", int(os.getenv("CREDIT_COST_PROFILE_IMAGE", "1")))
    
    # Store packages (key:credits:priceUSD)
    app.config.setdefault("STORE_PACKAGES", os.getenv(
        "STORE_PACKAGES",
        "starter:100:2.99,plus:500:9.99,mega:1200:19.99"
    ))

    # Stripe (optional)
    app.config.setdefault("STRIPE_PUBLIC_KEY", os.getenv("STRIPE_PUBLIC_KEY", ""))
    app.config.setdefault("STRIPE_SECRET_KEY", os.getenv("STRIPE_SECRET_KEY", ""))
    app.config.setdefault("STRIPE_WEBHOOK_SECRET", os.getenv("STRIPE_WEBHOOK_SECRET", ""))
    
    # Initialize database
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", db_url or "sqlite:///local.db")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault("SQLALCHEMY_ECHO", False)
    db.init_app(app)

    # Email / SMTP (DEV_MAIL_ECHO prints the reset link to logs if enabled)
    app.config.setdefault("SMTP_HOST", os.getenv("SMTP_HOST", ""))      # e.g., smtp.sendgrid.net
    app.config.setdefault("SMTP_PORT", int(os.getenv("SMTP_PORT", "587")))
    app.config.setdefault("SMTP_USER", os.getenv("SMTP_USER", ""))
    app.config.setdefault("SMTP_PASS", os.getenv("SMTP_PASS", ""))
    app.config.setdefault("SMTP_USE_TLS", os.getenv("SMTP_USE_TLS", "true").lower() == "true")
    app.config.setdefault("MAIL_FROM", os.getenv("MAIL_FROM", "no-reply@miniwordfinder.app"))
    app.config.setdefault("DEV_MAIL_ECHO", os.getenv("DEV_MAIL_ECHO", "true").lower() in ("1","true","yes"))
    # Reset token lifetime (minutes)
    app.config.setdefault("RESET_TOKEN_TTL_MIN", int(os.getenv("RESET_TOKEN_TTL_MIN", "30")))
    # Optional base URL (fallback if request.url_root isn't available)
    app.config.setdefault("APP_BASE_URL", os.getenv("APP_BASE_URL", "http://localhost:5000"))
    
    # ---- Store packages (key:credits:priceUSD) ----
    # Comma-separated; customize any time via env. Example shown below.
    app.config.setdefault("STORE_PACKAGES", os.getenv(
        "STORE_PACKAGES",
        "starter:500:4.99,plus:1200:9.99,mega:2600:19.99"
    ))

    # Stripe (optional)
    app.config.setdefault("STRIPE_PUBLIC_KEY", os.getenv("STRIPE_PUBLIC_KEY", ""))
    app.config.setdefault("STRIPE_SECRET_KEY", os.getenv("STRIPE_SECRET_KEY", ""))
    app.config.setdefault("STRIPE_WEBHOOK_SECRET", os.getenv("STRIPE_WEBHOOK_SECRET", ""))

    # Map package keys -> Stripe Price IDs (if using Stripe)
    # Example envs: STORE_PRICE_STARTER=price_xxx, STORE_PRICE_PLUS=price_yyy, STORE_PRICE_MEGA=price_zzz
    
    # Progressive pricing for Next Game
    app.config.setdefault("PROGRESSIVE_PAID_RUN_COSTS", os.getenv("PROGRESSIVE_PAID_RUN_COSTS", "1,1,1,2,2,3"))
    app.config.setdefault("DAILY_MAX_PAID_RUNS_BASE", int(os.getenv("DAILY_MAX_PAID_RUNS_BASE", "5")))
    app.config.setdefault("WEEKLY_PASS_EXTRA_PAID_RUNS", int(os.getenv("WEEKLY_PASS_EXTRA_PAID_RUNS", "0")))
    
    # Display name change
    app.config.setdefault("NAME_CHANGE_CREDIT_COST", int(os.getenv("NAME_CHANGE_CREDIT_COST", "1")))
    app.config.setdefault("NAME_CHANGE_COOLDOWN_DAYS", int(os.getenv("NAME_CHANGE_COOLDOWN_DAYS", "7")))
    
    # Post boost
    app.config.setdefault("BOOST_COST", int(os.getenv("BOOST_COST", "1")))
    app.config.setdefault("BOOST_HOURS", int(os.getenv("BOOST_HOURS", "12")))
    app.config.setdefault("BOOSTS_PER_DAY", int(os.getenv("BOOSTS_PER_DAY", "1")))
    
    return app

app = create_app()

# Initialize tables in app context
with app.app_context():
    db.create_all()
    
    # Seed admin user from environment variables
    _seed_admin_from_env()
    
    # Runtime patches for new columns
    try:
        eng = db.session.bind
        if eng and eng.dialect.name == "postgresql":
            # Progressive pricing patches
            db.session.execute("""
            DO $
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='weekly_pass_until')
              THEN ALTER TABLE users ADD COLUMN weekly_pass_until date; END IF;
              
              IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='display_name_changed_at')
              THEN ALTER TABLE users ADD COLUMN display_name_changed_at timestamptz; END IF;
              
              IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='community_posts' AND column_name='boost_until')
              THEN ALTER TABLE community_posts ADD COLUMN boost_until timestamptz; END IF;

              IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='boosts_day')
              THEN ALTER TABLE users ADD COLUMN boosts_day date; END IF;

              IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='boosts_used')
              THEN ALTER TABLE users ADD COLUMN boosts_used integer NOT NULL DEFAULT 0; END IF;
              
              IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='community_posts' AND column_name='is_hidden')
              THEN ALTER TABLE community_posts ADD COLUMN is_hidden boolean NOT NULL DEFAULT false; END IF;
              
              IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='is_banned')
              THEN ALTER TABLE users ADD COLUMN is_banned boolean NOT NULL DEFAULT false; END IF;
            END $;
            """)
            db.session.commit()
    except Exception as e:
        app.logger.warning(f"Database patches skipped: {e}")
    
    # Add SQLAlchemy attributes for new columns
    if not hasattr(User, "weekly_pass_until"):
        setattr(User, "weekly_pass_until", db.Column(db.Date))
    if not hasattr(User, "display_name_changed_at"):
        setattr(User, "display_name_changed_at", db.Column(db.DateTime(timezone=True)))
    if not hasattr(User, "boosts_day"):
        setattr(User, "boosts_day", db.Column(db.Date))
    if not hasattr(User, "boosts_used"):
        setattr(User, "boosts_used", db.Column(db.Integer, nullable=False, server_default="0"))
        
    # Import CommunityPost and add boost column
    from models import CommunityPost
    if not hasattr(CommunityPost, "boost_until"):
        setattr(CommunityPost, "boost_until", db.Column(db.DateTime(timezone=True)))
        
    # Add soft moderation fields
    if not hasattr(CommunityPost, "is_hidden"):
        setattr(CommunityPost, "is_hidden", db.Column(db.Boolean, nullable=False, server_default="false"))
    if not hasattr(User, "is_banned"):
        setattr(User, "is_banned", db.Column(db.Boolean, nullable=False, server_default="false"))

# Register CLI commands
_register_admin_cli()

# ---- Storage backend selection ----
# Options: "local", "s3", "supabase"
app.config.setdefault("STORAGE_BACKEND", os.getenv("STORAGE_BACKEND", "local").lower())

# S3 / R2 settings
app.config.setdefault("S3_ENDPOINT_URL", os.getenv("S3_ENDPOINT_URL", ""))  # e.g., "https://<accountid>.r2.cloudflarestorage.com"
app.config.setdefault("S3_REGION", os.getenv("S3_REGION", "us-east-1"))
app.config.setdefault("S3_BUCKET", os.getenv("S3_BUCKET", ""))
app.config.setdefault("S3_ACCESS_KEY_ID", os.getenv("S3_ACCESS_KEY_ID", ""))
app.config.setdefault("S3_SECRET_ACCESS_KEY", os.getenv("S3_SECRET_ACCESS_KEY", ""))
# Optional: if you front the bucket with a CDN/custom domain, set this and we'll build URLs from it.
app.config.setdefault("S3_CDN_BASE_URL", os.getenv("S3_CDN_BASE_URL", ""))  # e.g., "https://cdn.yourdomain.com"

# Supabase settings
app.config.setdefault("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
app.config.setdefault("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
app.config.setdefault("SUPABASE_BUCKET", os.getenv("SUPABASE_BUCKET", ""))  # bucket must exist

# Create uploads directory
os.makedirs(app.config["UPLOADS_DIR"], exist_ok=True)

# Lazy-init clients so the app can boot even if libs aren't installed for other backends.
_s3_client = None
_supabase_client = None

def _get_s3_client():
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    try:
        import boto3
    except Exception as e:
        raise RuntimeError("boto3 not installed; required for STORAGE_BACKEND=s3") from e

    _s3_client = boto3.client(
        "s3",
        region_name=app.config["S3_REGION"],
        endpoint_url=(app.config["S3_ENDPOINT_URL"] or None),
        aws_access_key_id=app.config["S3_ACCESS_KEY_ID"] or None,
        aws_secret_access_key=app.config["S3_SECRET_ACCESS_KEY"] or None,
    )
    return _s3_client

def _get_supabase_client():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    try:
        from supabase import create_client, Client
    except Exception as e:
        raise RuntimeError("supabase not installed; required for STORAGE_BACKEND=supabase") from e

    url = app.config["SUPABASE_URL"]
    key = app.config["SUPABASE_ANON_KEY"]
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY are required for STORAGE_BACKEND=supabase")

    _supabase_client = create_client(url, key)  # type: ignore
    return _supabase_client

# Register all routes
from api_routes import bp as api_bp
app.register_blueprint(api_bp)

# Register core routes
from routes import register_routes
register_routes(app, secret_key=SECRET_KEY, app_name=APP_NAME)

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
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper

def signer():
    return URLSafeTimedSerializer(SECRET_KEY)

# Admin session management helpers
def admin_logged_in() -> bool:
    return session.get("is_admin") is True

def require_admin():
    if not admin_logged_in():
        abort(401)

def check_user_banned(uid):
    """Check if user is banned, return JSON error if banned
    
    Usage in routes that create/modify community content:
        uid = session.get("user_id")
        banned_check = check_user_banned(uid)
        if banned_check: return banned_check
    """
    u = User.query.get(uid) if uid else None
    if u and u.is_banned:
        return jsonify({"error":"account restricted"}), 403
    return None

def require_user_admin():
    """Ensure current user is admin, raise 403 if not."""
    if "user_id" not in session:
        abort(401)  # Unauthorized
    
    user = User.query.get(session["user_id"])
    if not user or not user.is_admin:
        abort(403)  # Forbidden
    
    return user

def _seed_admin_from_env():
    """Create or update the admin user from env vars."""
    email = os.getenv("ADMIN_SEED_EMAIL")
    pwd = os.getenv("ADMIN_SEED_PASSWORD")

    if not email or not pwd:
        return  # nothing to do

    if len(pwd) < 6:
        app.logger.warning("ADMIN_SEED_PASSWORD is too short (min 6). Skipping admin seed.")
        return

    u = User.query.filter_by(email=email).first()
    if u is None:
        # Create username from email (before @ symbol)
        username = email.split('@')[0][:50]  # Limit to 50 chars
        # Ensure unique username
        counter = 1
        base_username = username
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"[:50]
            counter += 1
            
        u = User(email=email, username=username, is_admin=True)
        u.set_password(pwd)
        db.session.add(u)
        db.session.commit()
        app.logger.info("Admin seeded: %s (username: %s)", email, username)
    else:
        changed = False
        if not u.is_admin:
            u.is_admin = True
            changed = True
        if not u.check_password(pwd):
            u.set_password(pwd)
            changed = True
        if changed:
            db.session.commit()
            app.logger.info("Admin updated: %s", email)
        else:
            app.logger.info("Admin already up to date: %s", email)

def _register_admin_cli():
    """Register CLI commands for admin management."""
    
    @app.cli.command("admin-create")
    @click.option("--email", prompt=True, help="Admin email address")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
    def admin_create(email, password):
        """Create an admin user (or promote existing)."""
        if len(password) < 6:
            click.echo("Password must be at least 6 characters.")
            return
        
        with app.app_context():
            u = User.query.filter_by(email=email).first()
            if u is None:
                # Create username from email (before @ symbol)
                username = email.split('@')[0][:50]  # Limit to 50 chars
                # Ensure unique username
                counter = 1
                base_username = username
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}{counter}"[:50]
                    counter += 1
                    
                u = User(email=email, username=username, is_admin=True)
                u.set_password(password)
                db.session.add(u)
                click.echo(f"Admin created: {email} (username: {username})")
            else:
                u.is_admin = True
                u.set_password(password)
                click.echo(f"User promoted to admin: {email}")
            db.session.commit()

    @app.cli.command("admin-set-password")
    @click.option("--email", prompt=True, help="User email address")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="New password")
    def admin_set_password(email, password):
        """Reset password for an existing admin (or any user)."""
        if len(password) < 6:
            click.echo("Password must be at least 6 characters.")
            return
            
        with app.app_context():
            u = User.query.filter_by(email=email).first()
            if not u:
                click.echo("User not found.")
                return
            u.set_password(password)
            db.session.commit()
            click.echo(f"Password updated for: {email}")

def credit_txn(u: User, delta: int, reason: str, *, ref_table: str | None = None, ref_id: int | None = None, meta: dict | None = None, enforce_nonnegative: bool = True):
    """Adjusts u.mini_word_credits and logs a ledger row in one DB transaction step (call before commit)."""
    import json
    
    current = int(u.mini_word_credits or 0)
    new_bal = current + int(delta)
    if enforce_nonnegative and new_bal < 0:
        raise ValueError("insufficient credits")
    u.mini_word_credits = new_bal
    t = CreditTxn(user_id=u.id, delta=int(delta), reason=reason, ref_table=ref_table, ref_id=ref_id, meta=(json.dumps(meta) if meta else None))
    db.session.add(t)
    return t

# Store helper functions
def _parse_packages():
    """
    Returns dict: {key: {"key", "credits", "usd", "stripe_price"}}
    Stripe price id is read from env STORE_PRICE_<KEY_UPPER>
    """
    import decimal
    out = {}
    raw = (app.config["STORE_PACKAGES"] or "").split(",")
    for item in raw:
        item = item.strip()
        if not item or ":" not in item: continue
        key, credits, usd = item.split(":")
        key = key.strip().lower()
        price_env = f"STORE_PRICE_{key.upper()}"
        stripe_price = os.getenv(price_env, "")
        out[key] = {
            "key": key,
            "credits": int(credits),
            "usd": float(usd),
            "stripe_price": stripe_price,
        }
    return out

def _stripe_available():
    return bool(app.config["STRIPE_PUBLIC_KEY"] and app.config["STRIPE_SECRET_KEY"])

def _amount_cents(x: float | int | str):
    import decimal
    return int(decimal.Decimal(str(x)) * 100)

# Progressive pricing helpers
def _today_utc():
    from datetime import date, timezone
    return datetime.now(timezone.utc).date()

def _progressive_cost(u: User) -> int:
    # paid run number = next paid run index (1-based)
    idx = (u.paid_runs_used or 0) + 1
    tiers = [int(x.strip()) for x in (app.config["PROGRESSIVE_PAID_RUN_COSTS"] or "1,1,1,2,2,3").split(",") if x.strip()]
    if idx <= len(tiers): return tiers[idx-1]
    # after list ends, keep charging last tier
    return tiers[-1] if tiers else 1

def _paid_cap(u: User) -> int:
    extra = 0
    if getattr(u, "weekly_pass_until", None):
        extra = app.config["WEEKLY_PASS_EXTRA_PAID_RUNS"] if u.weekly_pass_until >= _today_utc() else 0
    return app.config.get("DAILY_MAX_PAID_RUNS_BASE", 5) + int(extra or 0)

def _reset_daily_if_needed(u: User):
    today = _today_utc()
    if getattr(u, "runs_day", None) != today:
        u.runs_day = today
        if hasattr(u, "free_runs_used"):
            u.free_runs_used = 0
        if hasattr(u, "paid_runs_used"):
            u.paid_runs_used = 0
    if getattr(u, "boosts_day", None) != today:
        u.boosts_day = today
        u.boosts_used = 0

# ---------------------- Routes: basics ----------------------
@app.route("/")
def index():
    return redirect(url_for("home") if "user_id" in session else url_for("login"))

@app.route("/home")
@login_required
def home():
    return render_template("home.html", app_name=APP_NAME)

@app.get("/forgot")
def forgot_form():
    return """
<!doctype html><meta charset="utf-8">
<title>Forgot Password</title>
<style>
  body{font-family:system-ui,Arial,sans-serif;margin:40px}
  .card{max-width:460px;margin:auto;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 1px 6px rgba(0,0,0,.08)}
  .btn{padding:8px 12px;border:1px solid #d1d5db;border-radius:10px;background:#fff;cursor:pointer}
  input{padding:10px;border:1px solid #d1d5db;border-radius:10px;width:100%}
  .muted{color:#6b7280;font-size:12px}
</style>
<div class="card">
  <h2>Forgot your password?</h2>
  <form method="post" action="/forgot">
    <label>Email</label>
    <input name="email" type="email" placeholder="you@example.com" required />
    <div style="margin-top:12px;display:flex;gap:8px;align-items:center">
      <button class="btn" type="submit">Send reset link</button>
      <a class="btn" href="/login">Back to login</a>
    </div>
    <div class="muted" style="margin-top:8px;">
      We'll send a link that lets you choose a new password. It expires in {{ttl}} minutes.
    </div>
  </form>
</div>
""".replace("{{ttl}}", str(app.config["RESET_TOKEN_TTL_MIN"]))

@app.post("/forgot")
def forgot_submit():
    # Always respond the same to prevent email enumeration
    email = (request.form.get("email") or "").strip().lower()
    msg = """
<!doctype html><meta charset="utf-8">
<title>Check your email</title>
<style>body{font-family:system-ui,Arial,sans-serif;margin:40px}.card{max-width:460px;margin:auto;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 1px 6px rgba(0,0,0,.08)}</style>
<div class="card"><h2>Check your email</h2>
<p>If an account exists for that address, we've sent a reset link. The link expires in %s minutes.</p>
<p><a href="/login">Back to login</a></p></div>
""" % app.config["RESET_TOKEN_TTL_MIN"]

    if not email:
        return msg

    u = User.query.filter_by(email=email).first()
    if u:
        token = _create_reset_token(u)
        reset_url = _abs_url(f"/reset/{token}")
        body = f"""Hi {u.display_name or u.username or 'there'},

We received a request to reset your Mini Word Finder password.

Click the link below to choose a new password (expires in {app.config["RESET_TOKEN_TTL_MIN"]} minutes):
{reset_url}

If you didn't request this, you can ignore this email.

— Mini Word Finder
"""
        _send_email(u.email, "Reset your Mini Word Finder password", body)

        # In dev echo mode, log the link; nothing is shown to the user.
        app.logger.info(f"[Reset link for {u.email}] {reset_url}")

    return msg

@app.get("/reset/<token>")
def reset_form(token):
    pr, u, err = _find_valid_reset(token)
    if err:
        return f"<div style='font-family:system-ui;margin:40px'><h2>Password reset</h2><p>{err}</p><p><a href='/forgot'>Request a new link</a></p></div>", 400
    return f"""
<!doctype html><meta charset="utf-8">
<title>Choose a new password</title>
<style>
  body{{font-family:system-ui,Arial,sans-serif;margin:40px}}
  .card{{max-width:460px;margin:auto;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 1px 6px rgba(0,0,0,.08)}}
  .row{{display:flex;gap:8px;align-items:center}}
  .btn{{padding:8px 12px;border:1px solid #d1d5db;border-radius:10px;background:#fff;cursor:pointer}}
  input{{padding:10px;border:1px solid #d1d5db;border-radius:10px;width:100%}}
  label{{font-size:14px;color:#374151}}
</style>
<div class="card">
  <h2>Choose a new password</h2>
  <form method="post" action="/reset/{token}" onsubmit="return checkMatch()">
    <label>New password (min 6)</label>
    <div class="row">
      <input id="npw" name="password" type="password" required minlength="6" />
      <button type="button" class="btn" onclick="toggle('npw', this)">👁</button>
    </div>
    <label style="margin-top:8px;">Confirm new password</label>
    <div class="row">
      <input id="npw2" name="confirm" type="password" required minlength="6" />
      <button type="button" class="btn" onclick="toggle('npw2', this)">👁</button>
    </div>
    <div class="row" style="margin-top:12px;justify-content:space-between">
      <button class="btn" type="submit">Update password</button>
      <a class="btn" href="/login">Back to login</a>
    </div>
  </form>
</div>
<script>
function toggle(id, btn){{ const i=document.getElementById(id); const show=i.type==='password'; i.type=show?'text':'password'; btn.textContent = show ? '🙈' : '👁'; }}
function checkMatch(){{ const a=document.getElementById('npw').value, b=document.getElementById('npw2').value; if(a!==b){{ alert('Passwords do not match'); return false; }} return true; }}
</script>
"""

@app.post("/reset/<token>")
def reset_submit(token):
    pr, u, err = _find_valid_reset(token)
    if err:
        return f"<div style='font-family:system-ui;margin:40px'><h2>Password reset</h2><p>{err}</p><p><a href='/forgot'>Request a new link</a></p></div>", 400
    pw = request.form.get("password") or ""
    conf = request.form.get("confirm") or ""
    if len(pw) < 6 or pw != conf:
        return "<div style='font-family:system-ui;margin:40px'>Invalid password or mismatch. <a href=''>Try again</a></div>", 400
    # Set new password and consume token
    u.set_password(pw)
    pr.used = True
    # Optional: invalidate all other unused tokens for this user
    PasswordReset.query.filter(
        PasswordReset.user_id == u.id,
        PasswordReset.used == False
    ).update({PasswordReset.used: True})
    db.session.commit()
    return """
<!doctype html><meta charset="utf-8">
<title>Password updated</title>
<style>body{font-family:system-ui,Arial,sans-serif;margin:40px}.card{max-width:460px;margin:auto;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 1px 6px rgba(0,0,0,.08)}</style>
<div class="card"><h2>Password updated</h2><p>Your password has been changed. You can now <a href="/login">log in</a>.</p></div>
"""

# ---------------------- Admin API Routes ----------------------

@app.post("/admin/api/purchase/<int:purchase_id>/refund")
def admin_purchase_refund(purchase_id):
    require_user_admin()
    data = request.get_json(silent=True) or {}
    note = (data.get("note") or "").strip()
    req_credits = int(data.get("credits") or 0)
    if not note:
        return jsonify({"error":"reason (note) is required"}), 400
    if req_credits <= 0:
        return jsonify({"error":"refund credits must be > 0"}), 400

    p = Purchase.query.get_or_404(purchase_id)
    if p.status not in ("succeeded", "created"):  # created (dev) could be treated as cancel
        return jsonify({"error": f"cannot refund in status {p.status}"}), 409

    u = User.query.get_or_404(p.user_id)

    # Check available credits (no negative balances)
    available = int(u.mini_word_credits or 0)
    if req_credits > available:
        return jsonify({"error": f"user has only {available} credits available to revoke"}), 409

    # Calculate $ portion for partial refunds (Stripe)
    cents_total = int(p.amount_usd_cents or 0)
    cents_refund = cents_total
    full_credit = int(p.credits or 0) if p.credits else 0
    is_partial = False
    if full_credit and req_credits < full_credit:
        # round to nearest cent
        cents_refund = round(cents_total * (req_credits / full_credit))
        is_partial = True

    # If Stripe, issue payment refund first
    if p.provider == "stripe":
        if not (os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_WEBHOOK_SECRET")):
            return jsonify({"error":"stripe not configured"}), 400
        try:
            import stripe
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
            # retrieve the Checkout Session -> payment_intent
            sess = stripe.checkout.Session.retrieve(p.provider_ref, expand=["payment_intent"])
            pi = sess["payment_intent"]["id"]
            stripe.Refund.create(payment_intent=pi, amount=cents_refund)
        except Exception as e:
            return jsonify({"error": f"stripe refund failed: {e}"}), 400

    # Revoke credits + write ledger
    try:
        credit_txn(u, -req_credits, "refund", ref_table="purchases", ref_id=p.id,
                   meta={"note": note, "provider": p.provider, "cents_refund": cents_refund})
    except ValueError:
        return jsonify({"error":"insufficient credits"}), 409

    # Update purchase status
    p.status = "refunded" if not is_partial else "refunded_partial"
    # append admin note to raw json
    try:
        import json as _json
        raw = {}
        if p.raw:
            try: raw = _json.loads(p.raw)
            except: raw = {"raw": p.raw}
        logs = raw.get("admin_notes", [])
        logs.append({"at": datetime.utcnow().isoformat(), "note": note, "credits": req_credits, "cents": cents_refund})
        raw["admin_notes"] = logs
        p.raw = _json.dumps(raw)
    except Exception:
        pass

    db.session.commit()
    return jsonify({"ok": True, "message": f"Refunded {req_credits} credits "
                                           f"({'partial' if is_partial else 'full'})",
                    "credits": u.mini_word_credits or 0, "purchase_status": p.status})

@app.post("/admin/api/user/<int:user_id>/adjust-credits")
def admin_user_adjust(user_id):
    require_user_admin()
    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta"))
    except:
        return jsonify({"error":"delta must be integer"}), 400
    note = (data.get("note") or "").strip()
    if not delta:
        return jsonify({"error":"delta cannot be 0"}), 400
    if not note:
        return jsonify({"error":"reason (note) is required"}), 400

    u = User.query.get_or_404(user_id)

    # Enforce nonnegative balances on negative adjustments
    if delta < 0 and (u.mini_word_credits or 0) < abs(delta):
        return jsonify({"error": f"user has only {u.mini_word_credits or 0} credits available"}), 409

    credit_txn(u, delta, "adjust", ref_table="users", ref_id=u.id, meta={"note": note})
    db.session.commit()
    return jsonify({"ok": True, "credits": u.mini_word_credits or 0})

# Admin dashboard route
@app.route("/admin")
@login_required
def admin_dashboard():
    require_user_admin()
    
    # Get recent purchases
    purchases = Purchase.query.order_by(desc(Purchase.created_at)).limit(50).all()
    
    # Get recent users
    users = User.query.order_by(desc(User.created_at)).limit(50).all()
    
    # Get recent transactions
    transactions = CreditTxn.query.order_by(desc(CreditTxn.created_at)).limit(100).all()
    
    return render_template("admin.html", 
                         purchases=purchases, 
                         users=users, 
                         transactions=transactions,
                         app_name=APP_NAME)

# ---------------------- New Admin Session Routes ----------------------

@app.get("/admin/login")
def admin_login_form():
    return render_template_string("""
<!doctype html><meta charset="utf-8">
<title>Admin Login – Mini Word Finder</title>
<style>
  body { font-family: system-ui, Arial, sans-serif; margin: 40px; line-height: 1.6; background:#fafafa; color:#1f2937; }
  .container { max-width: 460px; margin: auto; background:white; padding: 32px; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
  h1 { font-size: 28px; margin-bottom: 24px; text-align: center; }
  label { display: block; margin-bottom: 8px; font-weight: 500; }
  input { width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; margin-bottom: 16px; }
  button { width: 100%; padding: 12px; background: #4f46e5; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
  button:hover { background: #4338ca; }
  .alert { color: #dc2626; font-size: 14px; margin-bottom: 16px; text-align: center; }
</style>
<div class="container">
  <h1>Admin Login</h1>
  
  {% if error %}
  <p class="alert">{{ error }}</p>
  {% endif %}
  
  <form method="post">
    <label>Email Address</label>
    <input name="email" type="email" required placeholder="Enter your admin email">
    
    <label>Password</label>
    <input name="password" type="password" required placeholder="Enter your password">
    
    <button type="submit">Login as Admin</button>
  </form>
</div>
""", error=request.args.get('error'))

@app.post("/admin/login")
def admin_login():
    email = (request.form.get("email") or "").strip()
    password = (request.form.get("password") or "").strip()
    
    if not email or not password:
        return redirect(url_for("admin_login_form") + "?error=Email and password required")
    
    # Find user by email
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return redirect(url_for("admin_login_form") + "?error=Invalid credentials")
    
    # Check if user is admin
    if not user.is_admin:
        return redirect(url_for("admin_login_form") + "?error=Access denied - admin privileges required")
    
    # Set admin session
    session["is_admin"] = True
    session["admin_user_id"] = user.id
    return redirect(url_for("admin_dashboard_new"))

@app.get("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    session.pop("admin_user_id", None)
    return redirect("/community" if "/community" in [rule.rule for rule in app.url_map.iter_rules()] else "/")

@app.post("/admin/make-admin")
def make_admin():
    """Emergency route to make first admin - requires ADMIN_KEY"""
    key = request.form.get("key") or request.json.get("key") if request.json else None
    email = request.form.get("email") or request.json.get("email") if request.json else None
    
    if not key or key != os.getenv("ADMIN_KEY", "changeme"):
        return jsonify({"error": "Invalid admin key"}), 401
        
    if not email:
        return jsonify({"error": "Email required"}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    user.is_admin = True
    db.session.commit()
    return jsonify({"ok": True, "message": f"User {email} is now an admin"})

@app.get("/admin/dashboard")
def admin_dashboard_new():
    require_admin()
    from models import CommunityPost, CommunityReport
    
    posts = (CommunityPost.query
             .order_by(CommunityPost.created_at.desc())
             .limit(50).all())
    reports = (CommunityReport.query
               .order_by(CommunityReport.created_at.desc())
               .limit(50).all())
    users = (User.query.order_by(User.created_at.desc()).limit(50).all())
    return render_template_string("""
<!doctype html><meta charset="utf-8"><title>Admin – Mini Word Finder</title>
<style>
  body{font-family:system-ui,Arial,sans-serif;margin:24px}
  h2{margin:16px 0}
  table{border-collapse:collapse;width:100%}
  th,td{border:1px solid #e5e7eb;padding:8px;text-align:left;font-size:14px}
  th{background:#f3f4f6}
  .row{display:flex;gap:8px;flex-wrap:wrap}
  .btn{padding:6px 10px;border:1px solid #d1d5db;border-radius:8px;cursor:pointer;background:#fff}
  .ok{color:#065f46}
  .bad{color:#991b1b}
  .muted{color:#6b7280;font-size:12px}
</style>

<h1>Admin Panel</h1>
<div class="row" style="margin-bottom:12px">
  <a class="btn" href="/admin/logout">Logout</a>
  <a class="btn" href="/community">View Community</a>
</div>

<h2>Flagged Reports (latest 50)</h2>
<table>
  <tr><th>ID</th><th>Post</th><th>By</th><th>Reason</th><th>When</th><th>Actions</th></tr>
  {% for r in reports %}
    <tr>
      <td>{{ r.id }}</td>
      <td>#{{ r.post_id }}</td>
      <td>{{ r.user_id or "anon" }}</td>
      <td>{{ r.reason or "" }}</td>
      <td class="muted">{{ r.created_at.strftime("%Y-%m-%d %H:%M") }}</td>
      <td class="row">
        <button class="btn" onclick="hidePost({{ r.post_id }})">Hide Post</button>
        <button class="btn" onclick="unhidePost({{ r.post_id }})">Unhide</button>
        <button class="btn" onclick="deletePost({{ r.post_id }})">Delete</button>
        <button class="btn" onclick="banUserFromPost({{ r.post_id }})">Ban User</button>
        <button class="btn" onclick="clearReport({{ r.id }})">Clear Report</button>
      </td>
    </tr>
  {% endfor %}
</table>

<h2>Recent Posts (latest 50)</h2>
<table>
  <tr><th>ID</th><th>User</th><th>Hidden?</th><th>Points</th><th>Words</th><th>At</th><th>Actions</th></tr>
  {% for p in posts %}
    <tr>
      <td>{{ p.id }}</td>
      <td>{{ p.user_id }}</td>
      <td>{{ "Yes" if p.is_hidden else "No" }}</td>
      <td>{{ p.score.points }}</td>
      <td>{{ p.score.words_found }}</td>
      <td class="muted">{{ p.created_at.strftime("%Y-%m-%d %H:%M") }}</td>
      <td class="row">
        <button class="btn" onclick="hidePost({{ p.id }})">Hide</button>
        <button class="btn" onclick="unhidePost({{ p.id }})">Unhide</button>
        <button class="btn" onclick="deletePost({{ p.id }})">Delete</button>
        <button class="btn" onclick="banUser({{ p.user_id }})">Ban User</button>
        <button class="btn" onclick="unbanUser({{ p.user_id }})">Unban</button>
      </td>
    </tr>
  {% endfor %}
</table>

<h2>Recent Users (latest 50)</h2>
<table>
  <tr><th>ID</th><th>Name</th><th>Email</th><th>Banned?</th><th>Credits</th><th>Actions</th></tr>
  {% for u in users %}
    <tr>
      <td>{{ u.id }}</td>
      <td>{{ u.display_name or u.username or ("user_" ~ u.id) }}</td>
      <td>{{ u.email or "" }}</td>
      <td>{{ "Yes" if u.is_banned else "No" }}</td>
      <td>{{ u.mini_word_credits or 0 }}</td>
      <td class="row">
        <button class="btn" onclick="banUser({{ u.id }})">Ban</button>
        <button class="btn" onclick="unbanUser({{ u.id }})">Unban</button>
        <button class="btn" onclick="grantCredits({{ u.id }})">Grant Credits</button>
      </td>
    </tr>
  {% endfor %}
</table>

<script>
async function call(path, method="POST", body=null){
  const opts = { method, headers: {} };
  if(body){ opts.headers["Content-Type"]="application/json"; opts.body = JSON.stringify(body); }
  const r = await fetch(path, opts);
  const j = await r.json().catch(()=>({}));
  if(!r.ok){ alert(j.error || r.statusText); throw new Error(j.error||r.statusText); }
  return j;
}
async function hidePost(id){ if(!confirm("Hide post #"+id+"?")) return; await call(`/admin/api/post/${id}/hide`); location.reload(); }
async function unhidePost(id){ await call(`/admin/api/post/${id}/unhide`); location.reload(); }
async function deletePost(id){ if(!confirm("Delete post #"+id+"? This cannot be undone.")) return; await call(`/admin/api/post/${id}/delete`); location.reload(); }
async function banUser(id){ if(!confirm("Ban user #"+id+"?")) return; await call(`/admin/api/user/${id}/ban`); location.reload(); }
async function unbanUser(id){ await call(`/admin/api/user/${id}/unban`); location.reload(); }
async function banUserFromPost(postId){
  if(!confirm("Ban the author of post #"+postId+"?")) return;
  await call(`/admin/api/post/${postId}/ban-author`);
  location.reload();
}
async function clearReport(id){ await call(`/admin/api/report/${id}/clear`); location.reload(); }
async function grantCredits(uid){
  const amt = prompt("Grant how many credits?");
  if(!amt) return;
  await call(`/admin/api/user/${uid}/grant-credits`, "POST", { amount: Number(amt) });
  location.reload();
}
</script>
""", posts=posts, reports=reports, users=users)

# ---------------------- Terms & Guidelines Pages ----------------------

@app.get("/terms")
def terms_page():
    from datetime import datetime
    return render_template_string("""
<!doctype html><meta charset="utf-8">
<title>Terms & Privacy – Mini Word Finder</title>
<style>
  body { font-family: system-ui, Arial, sans-serif; margin: 40px; line-height: 1.6; background:#fafafa; color:#1f2937; }
  .container { max-width: 820px; margin: auto; background:white; padding: 32px; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
  h1 { font-size: 28px; margin-bottom: 8px; }
  h2 { font-size: 20px; margin-top: 28px; margin-bottom: 8px; }
  p { margin: 10px 0; }
  ul { margin: 10px 0 10px 24px; }
  a { color:#4f46e5; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .muted { color:#6b7280; font-size:14px; }
</style>
<div class="container">
  <h1>Terms of Service & Privacy Policy</h1>
  <p class="muted">Last updated: {{ now }}</p>

  <h2>1. Acceptance of Terms</h2>
  <p>By using <b>Mini Word Finder</b> (the "Service"), you agree to these Terms of Service and our Privacy Policy. If you do not agree, please discontinue use.</p>

  <h2>2. Use of Service</h2>
  <ul>
    <li>You may create an account and participate in our community features responsibly.</li>
    <li>You agree not to upload or share inappropriate, offensive, or illegal content.</li>
    <li>You are responsible for maintaining the security of your login information.</li>
  </ul>

  <h2>3. User Content</h2>
  <p>Any content you upload (including profile images and posts) remains yours, but by posting it you grant us a license to display it within the Service. We reserve the right to moderate or remove content that violates these Terms.</p>

  <h2>4. Mini Word Credits</h2>
  <p>Credits ("Mini Word Credits") are a virtual currency within the Service. Credits are non-refundable, non-transferable, and have no real-world monetary value. Changing your profile image consumes credits as described in the app.</p>

  <h2>5. Privacy</h2>
  <p>We respect your privacy:</p>
  <ul>
    <li>We collect only the information necessary to operate the Service (e.g., username, email, scores).</li>
    <li>Profile images you upload may be hosted on third-party storage providers (S3, Cloudflare R2, or Supabase).</li>
    <li>We do not sell or share your personal data with advertisers.</li>
  </ul>

  <h2>6. Cookies & Sessions</h2>
  <p>We use browser cookies/sessions to keep you logged in. You can clear these at any time in your browser settings.</p>

  <h2>7. Disclaimer of Warranty</h2>
  <p>The Service is provided "as is" without warranties of any kind. We do not guarantee uptime, error-free operation, or data permanence (though we do our best!).</p>

  <h2>8. Limitation of Liability</h2>
  <p>To the maximum extent permitted by law, we are not liable for damages resulting from your use of the Service.</p>

  <h2>9. Changes</h2>
  <p>We may update these Terms from time to time. Continued use of the Service after changes means you accept the new Terms.</p>

  <h2>10. Contact</h2>
  <p>If you have questions, please reach out at <a href="mailto:support@example.com">support@example.com</a>.</p>

  <p style="margin-top:24px;" class="muted">Thank you for being part of our community 💜</p>
</div>
""", now=datetime.utcnow().strftime("%B %d, %Y"))

@app.get("/guidelines")
def guidelines_page():
    from datetime import datetime
    return render_template_string("""
<!doctype html><meta charset="utf-8">
<title>Community Guidelines – Mini Word Finder</title>
<style>
  body { font-family: system-ui, Arial, sans-serif; margin: 40px; line-height: 1.6; background:#fafafa; color:#1f2937; }
  .container { max-width: 820px; margin: auto; background:white; padding: 32px; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,.08); }
  h1 { font-size: 28px; margin-bottom: 8px; }
  h2 { font-size: 20px; margin-top: 28px; margin-bottom: 8px; }
  p { margin: 10px 0; }
  ul { margin: 10px 0 10px 24px; }
  a { color:#4f46e5; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .muted { color:#6b7280; font-size:14px; }
</style>
<div class="container">
  <h1>Community Guidelines</h1>
  <p class="muted">Last updated: {{ now }}</p>

  <h2>1. Be Respectful</h2>
  <p>Treat everyone with kindness. Personal attacks, hate speech, or harassment are not allowed.</p>

  <h2>2. Share Appropriate Content</h2>
  <p>Keep posts and images safe for all audiences. Do not share offensive, explicit, or harmful material.</p>

  <h2>3. Play Fair</h2>
  <p>Do not cheat, spam, or manipulate leaderboards. Play honestly to keep the community fun for everyone.</p>

  <h2>4. Protect Privacy</h2>
  <ul>
    <li>Only share your own content and images.</li>
    <li>Do not share personal information (addresses, phone numbers, etc.).</li>
  </ul>

  <h2>5. Credit Usage</h2>
  <p>"Mini Word Credits" are part of the fun economy. Don't try to abuse or exploit the credit system.</p>

  <h2>6. Reporting & Moderation</h2>
  <p>If you see inappropriate content, please report it. Moderators may remove content or suspend accounts that break these rules.</p>

  <h2>7. Have Fun</h2>
  <p>Encourage others, celebrate wins, and enjoy the game together 🎉</p>

  <h2>Reminder</h2>
  <p>By participating in the community, you agree to follow these guidelines and our <a href="/terms">Terms & Privacy Policy</a>.</p>

  <p style="margin-top:24px;" class="muted">Thank you for helping us keep Mini Word Finder welcoming 💜</p>
</div>
""", now=datetime.utcnow().strftime("%B %d, %Y"))

# ---------------------- Store Routes ----------------------

@app.get("/store")
def store_page():
    pkgs = _parse_packages()
    stripe_enabled = _stripe_available()
    return render_template_string("""
<!doctype html><meta charset="utf-8">
<title>Store – Mini Word Finder</title>
<style>
  body{font-family:system-ui,Arial,sans-serif;margin:28px;background:#fafafa;color:#111827}
  .wrap{max-width:980px;margin:auto}
  .grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
  .title{font-weight:700}
  .btn{padding:8px 12px;border:1px solid #d1d5db;border-radius:10px;background:#fff;cursor:pointer}
  .btnp{padding:10px 12px;border:none;border-radius:10px;background:#111827;color:#fff;cursor:pointer}
  .muted{color:#6b7280;font-size:12px}
  .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
</style>
<div class="wrap">
  <div class="row" style="justify-content:space-between;margin-bottom:8px;">
    <h2>Buy Credits</h2>
    <div class="row">
      <a class="btn" href="/wallet">Wallet</a>
      <a class="btn" href="/community">Community</a>
      <a class="btn" href="/profile/{{ session.get('user_id') or '' }}">Profile</a>
      <a class="btn" href="/guidelines">Guidelines</a>
    </div>
  </div>
  <div class="muted" style="margin-top:6px">
    All credit sales are <b>final</b>. Refunds are only issued for billing errors, fraud, or other exceptional cases at our discretion.
  </div>
  <div class="muted">Use credits for profile image changes, extra "Next Games", post boosts, and more.</div>

  <div class="grid" style="margin-top:16px;">
    {% for k,p in pkgs.items() %}
    <div class="card">
      <div class="title">{{ p.credits }} Credits</div>
      <div class="muted" style="margin:6px 0">$ {{ '%.2f'|format(p.usd) }}</div>
      <div class="row" style="margin-top:8px;">
        <button class="btn" onclick="devBuy('{{ k }}')">Dev Add</button>
        {% if stripe_enabled and p.stripe_price %}
          <button class="btnp" onclick="buyStripe('{{ k }}')">Buy with Card</button>
        {% else %}
          <button class="btnp" disabled title="Stripe not configured">Buy with Card</button>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>

  <div style="margin-top:16px" class="muted">
    Balance: <span id="bal">…</span>
  </div>
</div>

<script>
async function getBal(){
  try{
    const r = await fetch('/api/credits/balance'); const j = await r.json();
    document.getElementById('bal').textContent = (j.credits ?? 'login');
  }catch(e){ document.getElementById('bal').textContent = 'login'; }
}
async function devBuy(key){
  if(!confirm('Add credits (dev mode): '+key+'?')) return;
  const r = await fetch('/api/store/dev-buy', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ key })});
  const j = await r.json(); if(!r.ok){ alert(j.error||'Error'); return; }
  alert('Added '+j.added+' credits'); getBal();
}
async function buyStripe(key){
  const r = await fetch('/api/store/checkout', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ key })});
  const j = await r.json(); if(!r.ok){ alert(j.error||'Error'); return; }
  location.href = j.url;
}
getBal();
</script>
""", pkgs=pkgs, stripe_enabled=stripe_enabled)

# ---------------------- Wallet Routes ----------------------

@app.get("/wallet")
def wallet_page():
    uid = session.get("user_id")
    if not uid: return redirect("/login")
    u = User.query.get_or_404(uid)
    txns = (CreditTxn.query
            .filter_by(user_id=uid)
            .order_by(CreditTxn.created_at.desc())
            .limit(200).all())
    purchases = (Purchase.query
                 .filter_by(user_id=uid)
                 .order_by(Purchase.created_at.desc())
                 .limit(50).all())
    return render_template_string("""
<!doctype html><meta charset="utf-8">
<title>Wallet – Mini Word Finder</title>
<style>
  body{font-family:system-ui,Arial,sans-serif;margin:28px;background:#fafafa;color:#111827}
  .wrap{max-width:980px;margin:auto}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:16px}
  table{width:100%;border-collapse:collapse} th,td{border-bottom:1px solid #eee;padding:8px;text-align:left;font-size:14px}
  th{background:#f9fafb}
  .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .pill{background:#eef2ff;border-radius:999px;padding:2px 8px;font-size:12px}
  .muted{color:#6b7280;font-size:12px}
</style>

<div class="wrap">
  <div class="row" style="justify-content:space-between;margin-bottom:10px;">
    <h2>Wallet</h2>
    <div class="row">
      <a class="pill" href="/store">Store</a>
      <a class="pill" href="/community">Community</a>
      <a class="pill" href="/profile/{{ u.id }}">Profile</a>
    </div>
  </div>

  <div class="card">
    <div class="row" style="justify-content:space-between;align-items:center;">
      <div><b>Balance:</b> {{ u.mini_word_credits or 0 }} credits</div>
      <div class="row">
        <a href="/store" class="btn" style="background:#4f46e5;color:white;padding:8px 16px;border-radius:8px;text-decoration:none;border:none;cursor:pointer;">Add Credits</a>
        <div class="muted" style="margin-left:12px;"><a href="/api/wallet/export.csv" style="color:#6b7280;">Download CSV</a></div>
      </div>
    </div>
  </div>

  <div class="card">
    <h3>Credit Activity</h3>
    <table>
      <thead><tr><th>When</th><th>Change</th><th>Reason</th><th>Details</th></tr></thead>
      <tbody>
        {% for t in txns %}
          <tr>
            <td class="muted">{{ t.created_at.strftime("%Y-%m-%d %H:%M") }}</td>
            <td>{% if t.delta >= 0 %}+{% endif %}{{ t.delta }}</td>
            <td>
              {% set r = t.reason %}
              {% if r == 'purchase' %}Purchase{% elif r == 'admin_grant' %}Admin Grant{% elif r == 'next_game' %}Next Game{% 
              elif r == 'profile_image' %}Profile Image{% elif r == 'name_change' %}Name Change{% elif r == 'boost' %}Post Boost{% 
              elif r == 'refund' %}Refund{% else %}{{ r }}{% endif %}
            </td>
            <td class="muted">
              {% if t.ref_table and t.ref_id %}{{ t.ref_table }}#{{ t.ref_id }}{% endif %}
              {% if t.meta %} — {{ t.meta|truncate(80, True) }}{% endif %}
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h3>Purchases</h3>
    <table>
      <thead><tr><th>When</th><th>Provider</th><th>Status</th><th>Credits</th><th>Amount</th></tr></thead>
      <tbody>
        {% for p in purchases %}
        <tr>
          <td class="muted">{{ p.created_at.strftime("%Y-%m-%d %H:%M") }}</td>
          <td>{{ p.provider }}</td>
          <td>{{ p.status }}</td>
          <td>{{ p.credits }}</td>
          <td>${{ '%.2f'|format((p.amount_usd_cents or 0)/100) }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="muted">Need more credits? Visit the <a href="/store">Store</a>.</div>
</div>
""", u=u, txns=txns, purchases=purchases)

@app.get("/api/wallet/txns")
def wallet_txns_json():
    uid = session.get("user_id")
    if not uid: return jsonify({"error":"login required"}), 401
    try: limit = min(int(request.args.get("limit", 200)), 1000)
    except: limit = 200
    txns = (CreditTxn.query.filter_by(user_id=uid)
            .order_by(CreditTxn.created_at.desc())
            .limit(limit).all())
    return jsonify({"count": len(txns), "txns": [{
        "id": t.id, "delta": t.delta, "reason": t.reason,
        "ref_table": t.ref_table, "ref_id": t.ref_id,
        "meta": t.meta, "created_at": t.created_at.isoformat()
    } for t in txns]})

@app.get("/api/wallet/export.csv")
def wallet_export_csv():
    from io import StringIO
    import csv
    uid = session.get("user_id")
    if not uid: return "login required", 401
    txns = (CreditTxn.query.filter_by(user_id=uid)
            .order_by(CreditTxn.created_at.desc()).all())
    sio = StringIO()
    w = csv.writer(sio)
    w.writerow(["id","created_at","delta","reason","ref_table","ref_id","meta"])
    for t in txns:
        w.writerow([t.id, t.created_at.isoformat(), t.delta, t.reason, t.ref_table or "", t.ref_id or "", t.meta or ""])
    from flask import Response
    return Response(
        sio.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=wallet.csv"}
    )

# ---------------------- Store API Routes ----------------------

@app.get("/api/credits/balance")
def api_credits_balance():
    uid = session.get("user_id")
    if not uid: return jsonify({"error":"login required"}), 401
    u = User.query.get(uid)
    return jsonify({"credits": u.mini_word_credits or 0 if u else 0})

@app.post("/api/store/dev-buy")
def api_store_dev_buy():
    import uuid
    uid = session.get("user_id")
    if not uid: return jsonify({"error":"login required"}), 401
    u = User.query.get(uid)
    key = ((request.get_json(silent=True) or {}).get("key") or "").lower()
    pkgs = _parse_packages()
    if key not in pkgs: return jsonify({"error":"unknown package"}), 400
    p = pkgs[key]

    # record "purchase"
    rec = Purchase(user_id=u.id, provider="dev", provider_ref=f"dev-{uuid.uuid4().hex}",
                   status="succeeded", credits=p["credits"],
                   amount_usd_cents=_amount_cents(p["usd"]), currency="usd",
                   raw=json.dumps({"package": key}))
    db.session.add(rec)

    # Use credit_txn to add credits and log transaction
    credit_txn(u, +p["credits"], "purchase", ref_table="purchases", ref_id=rec.id, 
               meta={"package": key, "provider":"dev"})
    db.session.commit()

    return jsonify({"ok": True, "added": p["credits"], "credits": u.mini_word_credits or 0})

@app.post("/api/store/checkout")
def api_store_checkout():
    if not _stripe_available(): return jsonify({"error":"stripe not configured"}), 400
    uid = session.get("user_id")
    if not uid: return jsonify({"error":"login required"}), 401
    u = User.query.get(uid)

    data = request.get_json(silent=True) or {}
    key = (data.get("key") or "").lower()
    pkgs = _parse_packages()
    pkg = pkgs.get(key)
    if not pkg: return jsonify({"error":"unknown package"}), 400
    if not pkg["stripe_price"]: return jsonify({"error":"no stripe price for package"}), 400

    try:
        import stripe
        stripe.api_key = app.config["STRIPE_SECRET_KEY"]
        session_obj = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{"price": pkg["stripe_price"], "quantity": 1}],
            success_url=url_for("store_page", _external=True) + "?success=1",
            cancel_url=url_for("store_page", _external=True) + "?cancel=1",
            metadata={"user_id": str(u.id), "package_key": key, "credits": str(pkg["credits"])},
        )
    except Exception as e:
        return jsonify({"error": f"stripe error: {e}"}), 400

    # record the intent (pending)
    rec = Purchase(user_id=u.id, provider="stripe", provider_ref=session_obj["id"],
                   status="created", credits=pkg["credits"],
                   amount_usd_cents=_amount_cents(pkg["usd"]), currency="usd",
                   raw=json.dumps({"package": key}))
    db.session.add(rec)
    db.session.commit()

    return jsonify({"ok": True, "url": session_obj["url"]})

@app.post("/webhooks/stripe")
def stripe_webhook():
    if not app.config["STRIPE_WEBHOOK_SECRET"]:
        return "Webhook not configured", 400
    import stripe
    stripe.api_key = app.config["STRIPE_SECRET_KEY"]

    payload = request.data
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig, secret=app.config["STRIPE_WEBHOOK_SECRET"]
        )
    except Exception as e:
        return f"Invalid payload: {e}", 400

    if event["type"] == "checkout.session.completed":
        s = event["data"]["object"]
        session_id = s["id"]
        uid = int((s.get("metadata") or {}).get("user_id") or 0)
        credits = int((s.get("metadata") or {}).get("credits") or 0)

        rec = Purchase.query.filter_by(provider="stripe", provider_ref=session_id).first()
        if rec and rec.status != "succeeded":
            u = User.query.get(uid)
            if u:
                # Use credit_txn to add credits and log transaction
                credit_txn(u, +credits, "purchase", ref_table="purchases", ref_id=rec.id, 
                          meta={"provider":"stripe"})
            rec.status = "succeeded"
            rec.raw = json.dumps(event, default=str)
            db.session.commit()
    return "ok", 200

# ---------------------- Admin API Actions ----------------------

@app.post("/admin/api/post/<int:post_id>/hide")
def admin_post_hide(post_id):
    if not admin_logged_in(): return jsonify({"error":"unauthorized"}), 401
    from models import CommunityPost
    p = CommunityPost.query.get_or_404(post_id)
    p.is_hidden = True
    db.session.commit()
    return jsonify({"ok":True})

@app.post("/admin/api/post/<int:post_id>/unhide")
def admin_post_unhide(post_id):
    if not admin_logged_in(): return jsonify({"error":"unauthorized"}), 401
    from models import CommunityPost
    p = CommunityPost.query.get_or_404(post_id)
    p.is_hidden = False
    db.session.commit()
    return jsonify({"ok":True})

@app.post("/admin/api/post/<int:post_id>/delete")
def admin_post_delete(post_id):
    if not admin_logged_in(): return jsonify({"error":"unauthorized"}), 401
    from models import CommunityPost
    p = CommunityPost.query.get_or_404(post_id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok":True})

@app.post("/admin/api/post/<int:post_id>/ban-author")
def admin_post_ban_author(post_id):
    if not admin_logged_in(): return jsonify({"error":"unauthorized"}), 401
    from models import CommunityPost
    p = CommunityPost.query.get_or_404(post_id)
    u = User.query.get(p.user_id)
    if u:
        u.is_banned = True
        db.session.commit()
    return jsonify({"ok":True})

@app.post("/admin/api/user/<int:user_id>/ban")
def admin_user_ban(user_id):
    if not admin_logged_in(): return jsonify({"error":"unauthorized"}), 401
    u = User.query.get_or_404(user_id)
    u.is_banned = True
    db.session.commit()
    return jsonify({"ok":True})

@app.post("/admin/api/user/<int:user_id>/unban")
def admin_user_unban(user_id):
    if not admin_logged_in(): return jsonify({"error":"unauthorized"}), 401
    u = User.query.get_or_404(user_id)
    u.is_banned = False
    db.session.commit()
    return jsonify({"ok":True})

@app.post("/admin/api/report/<int:report_id>/clear")
def admin_report_clear(report_id):
    if not admin_logged_in(): return jsonify({"error":"unauthorized"}), 401
    from models import CommunityReport
    r = CommunityReport.query.get_or_404(report_id)
    db.session.delete(r)
    db.session.commit()
    return jsonify({"ok":True})

@app.post("/admin/api/user/<int:user_id>/grant-credits")
def admin_user_grant_credits(user_id):
    if not admin_logged_in(): return jsonify({"error":"unauthorized"}), 401
    amt = int((request.get_json(silent=True) or {}).get("amount") or 0)
    if amt <= 0: return jsonify({"error":"amount>0 required"}), 400
    u = User.query.get_or_404(user_id)
    
    # Use credit_txn to grant credits and log transaction
    credit_txn(u, amt, "admin_grant", ref_table="users", ref_id=u.id, 
               meta={"admin_session": True})
    db.session.commit()
    return jsonify({"ok":True, "credits": u.mini_word_credits or 0})

# ---------------------- Community Reporting API ----------------------

def _hash_ip(ip: str) -> str:
    """Hash an IP address for privacy"""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]

@app.post("/api/community/<int:post_id>/report")
def api_community_report(post_id: int):
    from models import CommunityPost, CommunityReport
    post = CommunityPost.query.get_or_404(post_id)
    uid = session.get("user_id")
    real_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ip_hash = _hash_ip((real_ip or "").split(",")[0].strip())

    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip() or None
    if reason and len(reason) > 300:
        return jsonify({"error": "reason too long"}), 400

    # Prevent duplicate report by same user or IP
    existing = None
    if uid:
        existing = CommunityReport.query.filter_by(post_id=post.id, user_id=uid).first()
    if not existing and ip_hash:
        existing = CommunityReport.query.filter_by(post_id=post.id, ip_hash=ip_hash).first()
    if existing:
        return jsonify({"ok": True, "message": "already reported"})

    report = CommunityReport(post_id=post.id, user_id=uid or None, ip_hash=ip_hash, reason=reason)
    db.session.add(report)
    db.session.commit()
    return jsonify({"ok": True, "message": "report submitted"})

# ---------------------- Profile & Game API Routes ----------------------

@app.post("/api/profile/change-name")
def api_change_name():
    uid = session.get("user_id")
    if not uid: return jsonify({"error":"login required"}), 401
    u = User.query.get(uid)
    if u.is_banned: return jsonify({"error":"account restricted"}), 403

    new_name = (request.get_json(silent=True) or {}).get("display_name", "").strip()
    if not new_name or len(new_name) > 80:
        return jsonify({"error":"invalid display name"}), 400

    # cooldown
    cd_days = app.config["NAME_CHANGE_COOLDOWN_DAYS"]
    if u.display_name_changed_at:
        diff = datetime.now(timezone.utc) - u.display_name_changed_at
        if diff < timedelta(days=cd_days):
            left = cd_days - diff.days
            return jsonify({"error": f"name change on cooldown (~{left} day(s) left)"}), 429

    cost = app.config["NAME_CHANGE_CREDIT_COST"]
    if (u.mini_word_credits or 0) < cost:
        return jsonify({"error":"insufficient credits","needed":cost,"have":u.mini_word_credits or 0}), 402

    # Use credit_txn to subtract credits and log transaction
    credit_txn(u, -cost, "name_change", ref_table="users", ref_id=u.id)
    u.display_name = new_name
    u.display_name_changed_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"ok": True, "display_name": u.display_name, "credits": u.mini_word_credits or 0})

@app.post("/api/community/<int:post_id>/boost")
def api_boost_post(post_id: int):
    uid = session.get("user_id")
    if not uid: return jsonify({"error":"login required"}), 401
    u = User.query.get(uid)
    banned_check = check_user_banned(uid)
    if banned_check: return banned_check

    from models import CommunityPost
    p = CommunityPost.query.get_or_404(post_id)
    if p.user_id != uid: return jsonify({"error":"you can only boost your own post"}), 403
    if p.is_hidden: return jsonify({"error":"cannot boost hidden post"}), 400

    _reset_daily_if_needed(u)
    if (u.boosts_used or 0) >= app.config["BOOSTS_PER_DAY"]:
        return jsonify({"error":"daily boost limit reached"}), 429

    cost = app.config["BOOST_COST"]
    if (u.mini_word_credits or 0) < cost:
        return jsonify({"error":"insufficient credits","needed":cost,"have":u.mini_word_credits or 0}), 402

    # Use credit_txn to subtract credits and log transaction
    credit_txn(u, -cost, "boost", ref_table="community_posts", ref_id=p.id, 
               meta={"hours": app.config["BOOST_HOURS"]})
    u.boosts_used = (u.boosts_used or 0) + 1
    p.boost_until = datetime.now(timezone.utc) + timedelta(hours=app.config["BOOST_HOURS"])
    db.session.commit()
    return jsonify({"ok": True, "boost_until": p.boost_until.isoformat(), "credits": u.mini_word_credits or 0})

@app.post("/api/profile/set-image")
def api_profile_set_image():
    uid = session.get("user_id")
    if not uid: return jsonify({"error":"login required"}), 401
    user = User.query.get(uid)
    if user.is_banned: return jsonify({"error":"account restricted"}), 403
    
    data = request.get_json(silent=True) or {}
    img = (data.get("image_url") or "").strip()
    if not img: return jsonify({"error":"image_url required"}), 400
    if not (img.startswith("/static/") or img.startswith("https://")):
        return jsonify({"error":"invalid image_url"}), 400
    
    cost = app.config["CREDIT_COST_PROFILE_IMAGE"]
    is_change = bool(user.profile_image_url) and user.profile_image_url != img
    
    if is_change:
        if (user.mini_word_credits or 0) < cost:
            return jsonify({"error":"insufficient credits","needed":cost,"have":user.mini_word_credits or 0}), 402
        # Use credit_txn to subtract credits and log transaction
        credit_txn(user, -cost, "profile_image", ref_table="users", ref_id=user.id)
    
    user.profile_image_url = img
    db.session.commit()
    return jsonify({"ok": True, "charged": (cost if is_change else 0),
                    "credits": user.mini_word_credits or 0,
                    "profile_image_url": user.profile_image_url})

# Placeholder Next Game API (to be implemented with game logic)
@app.post("/api/game/next")
def api_next_game():
    uid = session.get("user_id")
    if not uid: return jsonify({"error":"login required"}), 401
    u = User.query.get(uid)
    if u.is_banned: return jsonify({"error":"account restricted"}), 403
    
    _reset_daily_if_needed(u)
    
    # Check if user has free runs left (example logic)
    daily_free_runs = app.config.get("DAILY_FREE_RUNS", 3)
    free_runs_used = getattr(u, "free_runs_used", 0) or 0
    
    if free_runs_used < daily_free_runs:
        # Free run
        u.free_runs_used = free_runs_used + 1
        db.session.commit()
        return jsonify({
            "ok": True, 
            "charged": 0,
            "free_left": max(0, daily_free_runs - u.free_runs_used),
            "paid_left": max(0, _paid_cap(u) - (u.paid_runs_used or 0)),
            "next_cost": _progressive_cost(u)
        })
    else:
        # Paid run path
        paid_cap = _paid_cap(u)
        if (u.paid_runs_used or 0) >= paid_cap:
            return jsonify({"error": "daily paid run cap reached"}), 429
        cost = _progressive_cost(u)
        if (u.mini_word_credits or 0) < cost:
            return jsonify({"error": "insufficient credits", "needed": cost, "have": u.mini_word_credits or 0}), 402
        
        # Use credit_txn to subtract credits and log transaction
        credit_txn(u, -cost, "next_game", ref_table="users", ref_id=u.id, 
                   meta={"paid_run_idx": (u.paid_runs_used or 0)+1, "cost": cost})
        u.paid_runs_used = (u.paid_runs_used or 0) + 1
        db.session.commit()
        
        return jsonify({
            "ok": True, 
            "charged": cost,
            "free_left": 0,
            "paid_left": max(0, _paid_cap(u) - u.paid_runs_used),
            "next_cost": _progressive_cost(u) if u.paid_runs_used < paid_cap else None
        })

# ---------------------- Community Routes ----------------------

@app.get("/community")
def community_page():
    from models import CommunityPost
    uid = session.get("user_id")
    if not uid: return redirect("/login")
    
    # Get posts with boosted posts first
    posts = (CommunityPost.query
             .filter(CommunityPost.is_hidden == False)
             .order_by(CommunityPost.boost_until.desc().nullslast(),
                       CommunityPost.likes_count.desc(),
                       CommunityPost.created_at.desc(),
                       CommunityPost.id.desc())
             .limit(100).all())
    
    return render_template_string("""
<!doctype html><meta charset="utf-8">
<title>Community – Mini Word Finder</title>
<style>
  body{font-family:system-ui,Arial,sans-serif;margin:28px;background:#fafafa;color:#111827}
  .wrap{max-width:980px;margin:auto}
  .card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:16px}
  .btn{padding:8px 12px;border:1px solid #d1d5db;border-radius:10px;background:#fff;cursor:pointer;font-size:12px}
  .btn:hover{background:#f9fafb}
  .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .muted{color:#6b7280;font-size:12px}
  .pill{background:#eef2ff;border-radius:999px;padding:2px 8px;font-size:11px}
  .boost-badge{background:#fde68a;color:#92400e;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold}
</style>

<div class="wrap">
  <div class="row" style="justify-content:space-between;margin-bottom:16px;">
    <h2>Community</h2>
    <div class="row">
      <a class="btn" href="/store">Store</a>
      <a class="btn" href="/wallet">Wallet</a>
      <a class="btn" href="/terms">Terms</a>
    </div>
  </div>

  {% for p in posts %}
  <div class="card">
    <div class="row" style="justify-content:space-between;margin-bottom:8px">
      <div>
        <strong>User #{{ p.user_id }}</strong>
        <span class="muted">{{ p.created_at.strftime("%Y-%m-%d %H:%M") }}</span>
      </div>
      <div class="row">
        {% if p.boost_until and p.boost_until > datetime.utcnow() %}
          <span class="boost-badge">⚡ Boosted</span>
        {% endif %}
      </div>
    </div>
    
    {% if p.caption %}
    <div style="margin:8px 0">{{ p.caption }}</div>
    {% endif %}
    
    <div class="row" style="margin-top:12px;justify-content:space-between">
      <div class="row">
        <button class="btn" onclick="likePost({{ p.id }})">👍 {{ p.likes_count or 0 }}</button>
        <button class="btn" onclick="reportPost({{ p.id }})">Report</button>
      </div>
      <div class="row">
        {% if current_user_id == p.user_id %}
          <button class="btn" onclick="boostPost({{ p.id }})">⚡ Boost</button>
        {% endif %}
      </div>
    </div>
  </div>
  {% else %}
  <div class="card">
    <p class="muted">No posts yet. Be the first to share something!</p>
  </div>
  {% endfor %}
  
  <div style="margin-top:24px;text-align:center">
    <button class="btn" onclick="createPost()">Create New Post</button>
  </div>
</div>

<script>
async function likePost(id){
  const r = await fetch(`/api/community/${id}/like`, {method:'POST'});
  const j = await r.json();
  if(!r.ok){ alert(j.error || 'Error'); return; }
  location.reload();
}

async function reportPost(id){
  const reason = prompt('Report reason (optional):');
  const r = await fetch(`/api/community/${id}/report`, {
    method:'POST', 
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({reason: reason || ''})
  });
  const j = await r.json();
  if(!r.ok){ alert(j.error || 'Error'); return; }
  alert('Report submitted');
}

async function boostPost(id){
  if(!confirm('Boost this post for {{ app.config.get("BOOST_COST", 1) }} credits?')) return;
  const r = await fetch(`/api/community/${id}/boost`, {method:'POST'});
  const j = await r.json();
  if(!r.ok){ alert(j.error || 'Error'); return; }
  alert('Post boosted!');
  location.reload();
}

function createPost(){
  // Placeholder for create post functionality
  alert('Create post functionality to be implemented');
}
</script>
""", posts=posts, current_user_id=uid, datetime=datetime, app=app)
