import os
from datetime import timedelta
from flask import Flask, request
from flask_login import LoginManager, current_user
from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the database instance from models
from models import db
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

    app.config.update(
        SESSION_COOKIE_SECURE=True,          # HTTPS only
        SESSION_COOKIE_SAMESITE="Lax",       # if cross-site, set "None"
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        SESSION_REFRESH_EACH_REQUEST=True,
        REMEMBER_COOKIE_DURATION=timedelta(days=7),
    )

    # Get database URL with fallback
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("WARNING: DATABASE_URL not set, using SQLite fallback")
        database_url = "sqlite:///local.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PREFERRED_URL_SCHEME"] = "https"

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

        # Get user from session for template context
        session_user = None
        if 'user_id' in session:
            session_user = db.session.get(User, session.get('user_id'))

        return dict(
            config={
                "HINT_CREDIT_COST": int(os.getenv("HINT_CREDIT_COST", "1")),
                "HINTS_PER_PUZZLE": int(os.getenv("HINTS_PER_PUZZLE", "3")),
                "HINT_ASSISTANT_NAME": os.getenv("HINT_ASSISTANT_NAME", "Word Cipher"),
            },
            current_user=session_user or current_user
        )

    @app.before_request
    def load_user():
        from flask import g, session
        # Make session user available globally and persistent
        session.permanent = True
        g.user = None
        user_id = session.get('user_id')
        if user_id:
            g.user = db.session.get(User, user_id)

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

        # Create all database tables
        db.create_all()

    @app.get("/health")
    def health():
        resp = {"ok": True}
        return resp, 200, {"Cache-Control": "no-store"}

    @app.after_request
    def add_cache_headers(resp):
        p = request.path
        if p.startswith('/static/'):
            resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
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
        # Keep CSP simple first; tighten later when you list all sources:
        resp.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'")
        return resp

    # Initialize background scheduler
    from extensions.scheduler import init_scheduler
    init_scheduler(app)

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