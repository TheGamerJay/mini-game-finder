from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, Index, text
import os

db = SQLAlchemy()

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

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(50), unique=True, index=True)
    display_name = db.Column(db.String(80))
    profile_image_url = db.Column(db.Text)
    profile_image_updated_at = db.Column(db.DateTime)
    display_name_updated_at = db.Column(db.DateTime)
    mini_word_credits = db.Column(db.Integer, default=0, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Score(db.Model):
    __tablename__ = "scores"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    mode = db.Column(db.String(16))
    total_words = db.Column(db.Integer, default=0)
    found_count = db.Column(db.Integer, default=0)
    duration_sec = db.Column(db.Integer)
    completed = db.Column(db.Boolean, default=False)
    seed = db.Column(db.BigInteger)
    category = db.Column(db.String(64))
    hints_used = db.Column(db.Integer, default=0)
    puzzle_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Legacy fields for compatibility
    game_mode = db.Column(db.String(32), default="mini_word_finder")
    points = db.Column(db.Integer, default=0)
    time_ms = db.Column(db.Integer, default=0)
    words_found = db.Column(db.Integer, default=0)
    max_streak = db.Column(db.Integer, default=0)
    played_at = db.Column(db.DateTime, default=datetime.utcnow)
    device = db.Column(db.String(64))
    ip_hash = db.Column(db.String(64))

class CreditTxn(db.Model):
    __tablename__ = "credit_txns"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    amount_delta = db.Column(db.Integer, nullable=False, default=0)
    reason = db.Column(db.Text)
    ref_txn_id = db.Column(db.Integer)
    idempotency_key = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Purchase(db.Model):
    __tablename__ = "purchases"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    package_key = db.Column(db.Text)
    credits = db.Column(db.Integer, default=0, nullable=False)
    amount_cents = db.Column(db.Integer, default=0, nullable=False)
    currency = db.Column(db.Text, default="usd", nullable=False)
    stripe_session_id = db.Column(db.Text)
    status = db.Column(db.Text, default="created", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Legacy fields
    provider = db.Column(db.String(24), default="stripe")
    provider_ref = db.Column(db.String(128))
    amount_usd_cents = db.Column(db.Integer, default=0)
    raw = db.Column(db.Text)

class PuzzleBank(db.Model):
    __tablename__ = "puzzle_bank"
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(16), nullable=False)
    category = db.Column(db.String(64))
    title = db.Column(db.String(160))
    words = db.Column(db.JSON, nullable=False)
    grid = db.Column(db.JSON, nullable=False)
    time_limit = db.Column(db.Integer)
    seed = db.Column(db.BigInteger)
    daily_date = db.Column(db.Date)
    active = db.Column(db.Boolean, default=True, nullable=False)
    puzzle_hash = db.Column(db.Text, nullable=False)
    answers = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Word(db.Model):
    __tablename__ = "words"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    length = db.Column(db.SmallInteger, nullable=False)
    pos = db.Column(db.Text)
    frequency = db.Column(db.Float)
    is_banned = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Text, unique=True, nullable=False)
    title = db.Column(db.Text, nullable=False)

class WordCategory(db.Model):
    __tablename__ = "word_categories"
    word_id = db.Column(db.Integer, db.ForeignKey("words.id", ondelete="CASCADE"), primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)

# Legacy aliases for compatibility
Words = Word
Categories = Category
WordCategories = WordCategory

class PuzzlePlays(db.Model):
    __tablename__ = "puzzle_plays"
    user_id = db.Column(db.Integer, nullable=False, primary_key=True)
    puzzle_id = db.Column(db.Integer, db.ForeignKey("puzzle_bank.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    played_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# Legacy models for compatibility
class PasswordReset(db.Model):
    __tablename__ = "password_resets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, index=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CommunityPost(db.Model):
    __tablename__ = "community_posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score_id = db.Column(db.Integer, db.ForeignKey("scores.id", ondelete="CASCADE"), nullable=False)
    caption = db.Column(db.String(300))
    likes_count = db.Column(db.Integer, nullable=False, default=0)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class CommunityLike(db.Model):
    __tablename__ = "community_likes"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    ip_hash = db.Column(db.String(64), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CommunityReport(db.Model):
    __tablename__ = "community_reports"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    ip_hash = db.Column(db.String(64), index=True)
    reason = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# New community system models
class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = db.Column(db.Text)
    image_url = db.Column(db.Text)
    image_width = db.Column(db.Integer)
    image_height = db.Column(db.Integer)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class PostReaction(db.Model):
    __tablename__ = "post_reactions"
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class PostReport(db.Model):
    __tablename__ = "post_reports"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)