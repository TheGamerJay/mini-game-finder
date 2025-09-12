# models.py
from __future__ import annotations
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, Index, text
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def _normalize_db_url(url: str | None) -> str | None:
    """
    Railway sometimes gives postgres://... — SQLAlchemy expects postgresql://...
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def init_db(app, *, echo: bool = False):
    """
    Call this from create_app() before returning the app.
    Will also auto-create tables if they don't exist.
    """
    db_url = _normalize_db_url(os.getenv("DATABASE_URL"))

    # Sensible defaults for Railway Postgres
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", db_url or "sqlite:///local.db")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault("SQLALCHEMY_ECHO", echo)

    db.init_app(app)

    # Optional: ensure UTC at the DB level for Postgres sessions
    @app.before_request
    def set_utc_timezone():
        if db.session.bind and db.session.bind.dialect.name == "postgresql":
            # Safe no-op on SQLite; Postgres only
            db.session.execute(text("SET TIME ZONE 'UTC'"))

    # Create tables if missing
    with app.app_context():
        db.create_all()


# ---------- Models ----------

class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # Keep either username OR email if you prefer minimal auth.
    username = db.Column(db.String(50), unique=True, index=True)
    email = db.Column(db.String(255), unique=True, index=True)
    password_hash = db.Column(db.String(255))

    scores = db.relationship("Score", back_populates="user", cascade="all, delete-orphan")

    # ---- helpers (optional) ----
    def set_password(self, raw: str):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return bool(self.password_hash) and check_password_hash(self.password_hash, raw)


class Score(db.Model, TimestampMixin):
    __tablename__ = "scores"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Mini Word Finder metrics — tweak as you like
    game_mode = db.Column(db.String(32), nullable=False, default="mini_word_finder")  # e.g., 'classic', 'timed'
    points = db.Column(db.Integer, nullable=False, default=0)
    time_ms = db.Column(db.Integer, nullable=False, default=0)       # total elapsed playtime
    words_found = db.Column(db.Integer, nullable=False, default=0)
    max_streak = db.Column(db.Integer, nullable=False, default=0)
    played_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    device = db.Column(db.String(64))      # e.g., 'desktop', 'mobile'
    ip_hash = db.Column(db.String(64))     # optional, if you hash IPs for anti-abuse

    user = db.relationship("User", back_populates="scores")

    __table_args__ = (
        # Common queries: leaderboard by mode/date, user history
        Index("ix_scores_user_id_played_at", "user_id", "played_at"),
        Index("ix_scores_game_mode_points", "game_mode", "points"),
    )