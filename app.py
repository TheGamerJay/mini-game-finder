import os
from flask import Flask
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

    # Configure session for better persistence
    app.config["SESSION_PERMANENT"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)

    # Get database URL with fallback
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("WARNING: DATABASE_URL not set, using SQLite fallback")
        database_url = "sqlite:///local.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PREFERRED_URL_SCHEME"] = "https"

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    db.init_app(app)
    login_manager.init_app(app)
    # Set login view for proper redirects
    login_manager.login_view = "core.login"
    login_manager.login_message = None  # Don't flash messages

    from models import User  # ensure models import after db init

    @login_manager.user_loader
    def load_user(uid):
        return User.query.get(int(uid))

    @app.context_processor
    def inject_cfg():
        # expose env-driven config to templates (read-only)
        return dict(
            config={
                "HINT_CREDIT_COST": int(os.getenv("HINT_CREDIT_COST", "1")),
                "HINTS_PER_PUZZLE": int(os.getenv("HINTS_PER_PUZZLE", "3")),
                "HINT_ASSISTANT_NAME": os.getenv("HINT_ASSISTANT_NAME", "Word Cipher"),
            },
            current_user=current_user
        )

    with app.app_context():
        from routes import bp as core_bp
        app.register_blueprint(core_bp)

        # Create all database tables
        db.create_all()

    @app.get("/health")
    def health(): return {"ok": True}, 200

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