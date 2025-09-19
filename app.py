import os, re, logging
from datetime import timedelta
from flask import Flask, request, jsonify, session
from flask_login import LoginManager, current_user, login_required
from werkzeug.middleware.proxy_fix import ProxyFix

# Challenge gate endpoints support
import psycopg2
from urllib.parse import urlparse

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    cleaned = (raw or "").strip()
    try:
        return int(cleaned)
    except ValueError:
        m = re.search(r'\d+', cleaned)
        if m:
            logging.warning("Coercing %s from %r to %s", name, raw, m.group(0))
            return int(m.group(0))
        logging.warning("Falling back to default for %s: %r", name, raw)
        return default

def bool_env(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in {"1","true","t","yes","y","on"}


# Import the database instance from models
from models import db
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

    app.config.update(
        SESSION_COOKIE_SECURE=True,          # HTTPS only
        SESSION_COOKIE_HTTPONLY=True,        # XSS protection
        SESSION_COOKIE_SAMESITE="Lax",       # if cross-site, set "None"
        # Remove PERMANENT_SESSION_LIFETIME to make sessions browser-session only
        SESSION_REFRESH_EACH_REQUEST=False,  # Don't extend session
        # Remove REMEMBER_COOKIE_DURATION to disable persistent login
        REMEMBER_COOKIE_SECURE=True,         # HTTPS only
        REMEMBER_COOKIE_HTTPONLY=True,       # XSS protection
        REMEMBER_COOKIE_SAMESITE="Lax",      # if cross-site, set "None"
    )

    # Get database URL with fallback
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("WARNING: DATABASE_URL not set, using SQLite fallback")
        database_url = "sqlite:///local.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PREFERRED_URL_SCHEME"] = os.getenv("PREFERRED_URL_SCHEME", "https")
    app.config.setdefault("ASSET_VERSION", os.environ.get("ASSET_VERSION", "2025-09-17-FINAL"))

    # --- Simple SMTP mail configuration (like your other project) ---
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "support@soulbridgeai.com").strip()

    # Debug the actual values
    logging.info(f"Raw SMTP_HOST: '{os.getenv('SMTP_HOST', '')}' -> cleaned: '{smtp_host}'")

    app.config.update(
        SMTP_HOST=smtp_host,
        SMTP_PORT=int_env("SMTP_PORT", 587),
        SMTP_USER=smtp_user,
        SMTP_PASS=smtp_pass,
        SMTP_FROM=smtp_from,
        SMTP_USE_TLS=bool_env("SMTP_USE_TLS", True),
        SMTP_USE_SSL=bool_env("SMTP_USE_SSL", False),
    )

    if smtp_host and smtp_from:
        logging.info(f"SMTP configured: {smtp_host}:{app.config['SMTP_PORT']}")
    else:
        logging.warning("SMTP not configured - reset links will be shown on page")
    # --- end mail configuration ---

    # Log mail backend selection (no secrets exposed)
    logging.info(
        "MAIL_BACKEND=%s | smtp_host_set=%s | smtp_port=%s | use_tls=%s | default_sender_set=%s",
        app.config.get("MAIL_BACKEND"),
        bool(app.config.get("MAIL_SERVER")),
        app.config.get("MAIL_PORT"),
        bool(app.config.get("MAIL_USE_TLS")),
        bool(app.config.get("MAIL_DEFAULT_SENDER")),
    )

    # Database engine optimization
    if database_url.startswith("sqlite"):
        app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {
            "connect_args": {"check_same_thread": False}
        })
    else:
        # PostgreSQL connection pool optimization
        app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {
            "pool_pre_ping": True,      # drops dead conns cleanly
            "pool_recycle": 1800,       # recycle every 30 min
            "pool_timeout": 30,
        })

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Make sure config is available in Jinja templates
    app.jinja_env.globals['config'] = app.config

    db.init_app(app)
    login_manager.init_app(app)
    # Set login view for proper redirects
    login_manager.login_view = "core.login"
    login_manager.login_message = None  # Don't flash messages

    from models import User  # ensure models import after db init

    @login_manager.user_loader
    def load_user(uid):
        return db.session.get(User, int(uid))

    @app.context_processor
    def inject_cfg():
        # expose env-driven config to templates (read-only)
        from flask import session
        from csrf_utils import rotate_csrf_token

        # Get user from session for template context
        session_user = None
        if 'user_id' in session:
            session_user = db.session.get(User, session.get('user_id'))

        # Generate CSRF token for authenticated users
        csrf_token = None
        if session_user or (current_user and current_user.is_authenticated):
            if 'csrf_token' not in session:
                csrf_token = rotate_csrf_token()
            else:
                csrf_token = session['csrf_token']

        return dict(
            config={
                "HINT_CREDIT_COST": int(os.getenv("HINT_CREDIT_COST", "1")),
                "HINTS_PER_PUZZLE": int(os.getenv("HINTS_PER_PUZZLE", "3")),
                "HINT_ASSISTANT_NAME": os.getenv("HINT_ASSISTANT_NAME", "Word Cipher"),
                # Block B feature flags
                "LEARN_MODE_ENABLED": os.getenv("LEARN_MODE_ENABLED", "true").lower() == "true",
                "REVEAL_WITH_LESSON_ENABLED": os.getenv("REVEAL_WITH_LESSON_ENABLED", "true").lower() == "true",
                "AUTO_TEACH_ON_FIND_DEFAULT_NO_TIMER": os.getenv("AUTO_TEACH_ON_FIND_DEFAULT_NO_TIMER", "true").lower() == "true",
                "AUTO_TEACH_ON_FIND_DEFAULT_TIMER": os.getenv("AUTO_TEACH_ON_FIND_DEFAULT_TIMER", "false").lower() == "true",
                "GAME_COST": int(os.getenv("GAME_COST", "5")),
                "REVEAL_COST": int(os.getenv("REVEAL_COST", "5")),
                "FREE_GAMES_LIMIT": int(os.getenv("FREE_GAMES_LIMIT", "5")),
            },
            current_user=session_user or current_user,
            csrf_token=csrf_token
        )

    @app.before_request
    def _global_csrf_guard():
        # Enforce CSRF automatically for all unsafe methods unless exempt
        from csrf_utils import should_enforce_csrf, ensure_csrf_or_403
        if should_enforce_csrf():
            fail = ensure_csrf_or_403()
            if fail is not None:
                return fail

    @app.before_request
    def load_user():
        from flask import g, session
        # Make session user available globally and persistent
        session.permanent = True
        g.user = None
        user_id = session.get('user_id')
        if user_id:
            g.user = db.session.get(User, user_id)

    @app.before_request
    def require_login():
        from flask import request, redirect, url_for
        from flask_login import current_user

        # Allow static files
        if request.endpoint and request.endpoint.startswith('static'):
            return

        # Allow auth endpoints and main navigation routes
        public_endpoints = [
            'core.login', 'core.register', 'core.reset_request', 'core.reset_token',
            'core.favicon', 'core.robots_txt', 'core.home', 'core.index',
            'core.terms', 'core.policy', 'core.guide', 'core.faq', 'core.health',
            'arcade.tictactoe', 'arcade.connect4', 'arcade.api_game_start', 'arcade.api_game_result',
            'arcade.api_leaderboard'
        ]

        if request.endpoint in public_endpoints:
            return

        # Check if user is authenticated
        if not current_user.is_authenticated:
            return redirect(url_for('core.login'))

    # Ensure uploads directory exists
    upload_dir = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    with app.app_context():
        import routes as core_routes
        app.register_blueprint(core_routes.bp)

        # Register gaming platform blueprints
        from gaming_routes.wallet import wallet_bp
        from gaming_routes.badges import badges_bp
        from gaming_routes.gaming_community import gaming_community_bp
        from gaming_routes.wars import wars_bp
        from gaming_routes.leaderboard import leaderboard_bp

        app.register_blueprint(wallet_bp)
        app.register_blueprint(badges_bp)
        app.register_blueprint(gaming_community_bp)
        app.register_blueprint(wars_bp)
        app.register_blueprint(leaderboard_bp)

        # Register diagnostic routes
        from diag_sched import bp as diag_bp
        app.register_blueprint(diag_bp)

        from diag_auth import bp as diag_auth_bp
        app.register_blueprint(diag_auth_bp)

        # Register Block B blueprints (Credits System)
        from blueprints import credits_bp, game_bp, prefs_bp
        app.register_blueprint(credits_bp)
        app.register_blueprint(game_bp)
        app.register_blueprint(prefs_bp)

        # Register Riddle Master Mini Game
        from blueprints.riddle import riddle_bp
        app.register_blueprint(riddle_bp)

        # Register Arcade Games
        from blueprints.arcade import arcade_bp
        app.register_blueprint(arcade_bp)

        # Create all database tables
        db.create_all()

    @app.get("/health")
    def health():
        resp = {"ok": True}
        return resp, 200, {"Cache-Control": "no-store"}

    # Diagnostic route (dev-only when explicitly enabled)
    if os.getenv("ENABLE_DIAG_MAIL") == "1" and os.getenv("FLASK_ENV") != "production":
        @app.get("/__diag/mail")
        def __diag_mail():
            c = app.config
            return {
                "MAIL_BACKEND": c.get("MAIL_BACKEND"),
                "smtp_host_set": bool(c.get("MAIL_SERVER")),
                "smtp_port": c.get("MAIL_PORT"),
                "use_tls": bool(c.get("MAIL_USE_TLS")),
                "default_sender": c.get("MAIL_DEFAULT_SENDER"),
                "has_username": bool(c.get("MAIL_USERNAME")),
                "has_password": bool(c.get("MAIL_PASSWORD")),
            }, 200

    @app.post("/__csp-report")
    def csp_report():
        # Keep this endpoint cheap and safe
        raw = request.get_data(cache=False, as_text=True, parse_form_data=False)
        if not raw:
            return "", 204

        # Cap payload to avoid log spam
        if len(raw) > 32_768:  # 32 KB cap
            app.logger.warning("CSP violation (truncated, >32KB)")
            return "", 204

        ctype = (request.content_type or "").lower()

        try:
            data = request.get_json(silent=True)
        except Exception:
            data = None

        report = None
        if isinstance(data, dict):
            # Legacy format: {"csp-report": {...}}
            report = data.get("csp-report") or data
        else:
            # Fallback: try to parse manually for odd content-types
            try:
                import json
                j = json.loads(raw)
                report = j.get("csp-report") or j
            except Exception:
                report = {"_raw": raw[:2000]}  # last resort

        # Redact potentially sensitive fields
        def _scrub(url: str) -> str:
            if not isinstance(url, str):
                return url
            # Strip query fragments to avoid logging PII
            return url.split("?")[0].split("#")[0]

        if isinstance(report, dict):
            for k in ("blocked-uri", "document-uri", "referrer"):
                if k in report:
                    report[k] = _scrub(report[k])

        app.logger.warning(f"CSP violation: {report}")
        return "", 204

    @app.after_request
    def add_cache_headers(resp):
        p = request.path
        if p.startswith('/static/'):
            resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            resp.headers.setdefault('Vary', 'Accept-Encoding')
        else:
            # Safety for dynamic pages (especially /login, /home)
            if resp.mimetype in ('text/html', 'text/html; charset=utf-8'):
                resp.headers['Cache-Control'] = 'no-store'
        return resp

    @app.after_request
    def add_security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        # CSP with unsafe-inline temporarily (due to legacy inline styles in templates)
        resp.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'")
        # Modern CSP reporting
        resp.headers.setdefault(
            "Report-To",
            '{"group":"csp","max_age":10886400,"endpoints":[{"url":"/__csp-report"}]}'
        )
        # CSP reporting for observing violations (parallel policy)
        resp.headers.setdefault(
            "Content-Security-Policy-Report-Only",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
            "report-uri /__csp-report; report-to csp"
        )
        # Modern security headers (only if always HTTPS)
        if app.config.get("PREFERRED_URL_SCHEME") == "https":
            resp.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        resp.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        resp.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return resp

    # Initialize background scheduler
    from extensions.scheduler import init_scheduler
    init_scheduler(app)

    # Challenge Gate API endpoints
    @app.get("/api/challenge/status")
    def challenge_status():
        # Prefer Flask-Login, else session['uid'], else anonymous
        user_id = None
        if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
            user_id = current_user.id
        elif "uid" in session:
            user_id = session["uid"]

        if not user_id:
            # Not logged in: fall back to showing gate once per tab on the frontend
            return jsonify({"ok": True, "logged_in": False, "accepted": False})

        try:
            # Check if challenge_gate_accepted column exists
            result = None
            try:
                result = db.session.execute(
                    "SELECT challenge_gate_accepted FROM users WHERE id = :user_id",
                    {"user_id": user_id}
                )
                row = result.fetchone()
                accepted = bool(row[0]) if row else False
            except Exception as column_error:
                # Column might not exist yet, treat as not accepted
                app.logger.warning(f"challenge_gate_accepted column not found: {column_error}")
                accepted = False

            return jsonify({"ok": True, "logged_in": True, "accepted": accepted})
        except Exception as e:
            app.logger.error(f"Error checking challenge gate status: {e}")
            # Fallback to not accepted on error
            return jsonify({"ok": True, "logged_in": True, "accepted": False})

    @app.post("/api/challenge/accept")
    def challenge_accept():
        user_id = None
        if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
            user_id = current_user.id
        elif "uid" in session:
            user_id = session["uid"]

        if not user_id:
            # If anonymous, just acknowledge so UI can proceed (no DB write)
            return jsonify({"ok": True, "logged_in": False, "accepted": False})

        try:
            try:
                db.session.execute(
                    "UPDATE users SET challenge_gate_accepted = :accepted WHERE id = :user_id",
                    {"accepted": True, "user_id": user_id}
                )
                db.session.commit()
                app.logger.info(f"User {user_id} accepted challenge gate")
                return jsonify({"ok": True, "logged_in": True, "accepted": True})
            except Exception as update_error:
                # Column might not exist yet, gracefully handle
                db.session.rollback()
                app.logger.warning(f"Could not update challenge_gate_accepted: {update_error}")
                # Return success anyway so UI doesn't break
                return jsonify({"ok": True, "logged_in": True, "accepted": True})

        except Exception as e:
            app.logger.error(f"Error accepting challenge gate: {e}")
            return jsonify({"ok": False, "error": "Failed to accept challenge gate"}), 500

    # Register CLI commands
    from cli import register_cli
    register_cli(app)

    return app

app = create_app()

# Import everything from your original app.py for compatibility
import secrets, datetime
from functools import wraps
import click
from flask import (
    render_template, request, redirect, url_for,
    session, flash, jsonify, abort, render_template_string
)
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import text, desc, func
import hashlib
import json, uuid
import smtplib
from email.message import EmailMessage
from hashlib import sha256
from datetime import timedelta, timezone, datetime

# Import your existing models for compatibility
from models import User, Score, PasswordReset, Purchase, CreditTxn

# Set up constants from your original app
APP_NAME = os.environ.get("APP_NAME", "Mini Word Finder")
SECRET_KEY = os.environ.get("FLASK_SECRET", os.environ.get("SECRET_KEY", secrets.token_hex(32)))

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
        base = app.config.get("APP_BASE_URL", "").rstrip("/")
    return base + path

def _send_email(to_email: str, subject: str, text_body: str) -> bool:
    # Dev-friendly: echo to logs instead of sending
    if app.config.get("DEV_MAIL_ECHO", True):
        app.logger.info(f"[MAIL to {to_email}] {subject}\n{text_body}")
        return True
    host = app.config.get("SMTP_HOST")
    if not host:
        app.logger.warning("SMTP not configured; falling back to DEV_MAIL_ECHO")
        return False

    try:
        with smtplib.SMTP(host, app.config.get("SMTP_PORT", 587)) as server:
            server.starttls()
            server.login(app.config.get("SMTP_USER"), app.config.get("SMTP_PASS"))

            msg = EmailMessage()
            msg["From"] = app.config.get("SMTP_FROM")
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.set_content(text_body)

            server.send_message(msg)
        return True
    except Exception as e:
        app.logger.error(f"Failed to send email: {e}")
        return False

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)