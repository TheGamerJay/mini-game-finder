# models.py
from __future__ import annotations
import os
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, Index, text
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

def _normalize_db_url(url: str | None) -> str | None:
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

def init_db(app, *, echo: bool = False):
    db_url = _normalize_db_url(os.getenv("DATABASE_URL"))
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", db_url or "sqlite:///local.db")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault("SQLALCHEMY_ECHO", echo)
    db.init_app(app)

    @app.before_request
    def set_utc_timezone():
        if db.session.bind and db.session.bind.dialect.name == "postgresql":
            db.session.execute(text("SET TIME ZONE 'UTC'"))

    with app.app_context():
        db.create_all()

# ---------- Models ----------

class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class User(db.Model, TimestampMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, index=True)
    email = db.Column(db.String(255), unique=True, index=True)
    password_hash = db.Column(db.String(255))

    # Profile & admin
    display_name = db.Column(db.String(80), index=True)
    profile_image_url = db.Column(db.String(512))
    mini_word_credits = db.Column(db.Integer, nullable=False, server_default="0")
    is_banned = db.Column(db.Boolean, nullable=False, server_default="false")
    is_admin = db.Column(db.Boolean, nullable=False, server_default="false")

    scores = db.relationship("Score", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw: str):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return bool(self.password_hash) and check_password_hash(self.password_hash, raw)

class Score(db.Model, TimestampMixin):
    __tablename__ = "scores"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    game_mode = db.Column(db.String(32), nullable=False, default="mini_word_finder")
    points = db.Column(db.Integer, nullable=False, default=0)
    time_ms = db.Column(db.Integer, nullable=False, default=0)
    words_found = db.Column(db.Integer, nullable=False, default=0)
    max_streak = db.Column(db.Integer, nullable=False, default=0)
    played_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    device = db.Column(db.String(64))
    ip_hash = db.Column(db.String(64))

    user = db.relationship("User", back_populates="scores")

    __table_args__ = (
        Index("ix_scores_user_id_played_at", "user_id", "played_at"),
        Index("ix_scores_game_mode_points", "game_mode", "points"),
    )

class CommunityPost(db.Model, TimestampMixin):
    __tablename__ = "community_posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score_id = db.Column(db.Integer, db.ForeignKey("scores.id", ondelete="CASCADE"), nullable=False)
    caption = db.Column(db.String(300))
    likes_count = db.Column(db.Integer, nullable=False, default=0)
    is_hidden = db.Column(db.Boolean, nullable=False, server_default="false")

    user = db.relationship("User")
    score = db.relationship("Score")

    __table_args__ = (
        Index("ix_posts_user_id_created", "user_id", "created_at"),
    )

class PasswordReset(db.Model, TimestampMixin):
    __tablename__ = "password_resets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, index=True, nullable=False)  # sha256(token)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
        Index("ix_posts_likes_created", "likes_count", "created_at"),
    )

class CommunityLike(db.Model, TimestampMixin):
    __tablename__ = "community_likes"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    ip_hash = db.Column(db.String(64), index=True)

    __table_args__ = (
        Index("uq_like_post_user", "post_id", "user_id", unique=True),
        Index("uq_like_post_ip", "post_id", "ip_hash", unique=True),
    )

class CommunityReport(db.Model, TimestampMixin):
    __tablename__ = "community_reports"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    ip_hash = db.Column(db.String(64), index=True)
    reason = db.Column(db.String(300))

    __table_args__ = (
        db.UniqueConstraint("post_id", "user_id", name="uq_report_post_user"),
        db.UniqueConstraint("post_id", "ip_hash", name="uq_report_post_ip"),
    )

class Purchase(db.Model, TimestampMixin):
    __tablename__ = "purchases"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    provider = db.Column(db.String(24), nullable=False)          # "dev" | "stripe"
    provider_ref = db.Column(db.String(128), index=True)         # e.g. Stripe session id
    status = db.Column(db.String(24), nullable=False, default="created")  # created/succeeded/failed/refunded

    credits = db.Column(db.Integer, nullable=False, default=0)   # credits to grant on success
    amount_usd_cents = db.Column(db.Integer, nullable=False, default=0)
    currency = db.Column(db.String(8), nullable=False, default="usd")

    raw = db.Column(db.Text)                                     # provider payload (json string)
    
    user = db.relationship("User")

class CreditTxn(db.Model, TimestampMixin):
    __tablename__ = "credit_txns"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    delta = db.Column(db.Integer, nullable=False)  # + or -
    reason = db.Column(db.String(40), nullable=False)  # purchase|admin_grant|profile_image|refund|adjust
    ref_table = db.Column(db.String(30))  # e.g., "purchases", "community_posts", "users"
    ref_id = db.Column(db.Integer)
    meta = db.Column(db.Text)  # optional JSON string (context)
    
    user = db.relationship("User")

class Purchase(db.Model, TimestampMixin):
    __tablename__ = "purchases"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    provider = db.Column(db.String(24), nullable=False)          # "dev" | "stripe"
    provider_ref = db.Column(db.String(128), index=True)         # e.g. Stripe session id
    status = db.Column(db.String(24), nullable=False, default="created")  # created/succeeded/failed/refunded

    credits = db.Column(db.Integer, nullable=False, default=0)   # credits to grant on success
    amount_usd_cents = db.Column(db.Integer, nullable=False, default=0)
    currency = db.Column(db.String(8), nullable=False, default="usd")

    raw = db.Column(db.Text)                                     # provider payload (json string)
    
    user = db.relationship("User")

class CreditTxn(db.Model, TimestampMixin):
    __tablename__ = "credit_txns"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    delta = db.Column(db.Integer, nullable=False)  # + or -
    reason = db.Column(db.String(40), nullable=False)  # purchase|admin_grant|profile_image|refund|adjust
    ref_table = db.Column(db.String(30))  # e.g., "purchases", "community_posts", "users"
    ref_id = db.Column(db.Integer)
    meta = db.Column(db.Text)  # optional JSON string (context)
    
    user = db.relationship("User")