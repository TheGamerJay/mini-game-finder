# 🐍 Block B — Flask blueprints: Credits API
# This blueprint handles credit balance and spending operations

from flask import Blueprint, request, jsonify, abort, session, current_app
from models import db, User
from routes import get_session_user
from csrf_utils import require_csrf
from sqlalchemy import text
import os

credits_bp = Blueprint("credits", __name__, url_prefix="/api/credits")

def _get_user_id():
    """Get current user ID from session or Flask-Login"""
    # Try session-based auth first (matches existing pattern)
    user = get_session_user()
    if user:
        return user.id

    # Fallback to Flask-Login if available
    from flask_login import current_user
    if current_user and current_user.is_authenticated:
        return current_user.id

    return None

@credits_bp.route("/balance", methods=["GET"])
def balance():
    """Get user's current credit balance"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    try:
        # Use SQLAlchemy to be database-agnostic
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Use the existing mini_word_credits field
        balance = user.mini_word_credits or 0

        return jsonify({
            "ok": True,
            "balance": balance,
            "user_id": user_id
        })

    except Exception as e:
        current_app.logger.error(f"Error getting credit balance for user {user_id}: {e}")
        return jsonify({"error": "Failed to get balance"}), 500

@credits_bp.route("/history", methods=["GET"])
def history():
    """Get user's credit usage history"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    # Parse query parameters
    limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 records
    offset = int(request.args.get('offset', 0))

    try:
        # For now, return empty history since we're using simple balance tracking
        # This can be enhanced later with a proper credit_usage table
        return jsonify({
            "ok": True,
            "history": [],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": 0,
                "has_more": False
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error getting credit history for user {user_id}: {e}")
        return jsonify({"error": "Failed to get history"}), 500

def spend_credits(user_id, amount, reason, puzzle_id=None, word_id=None):
    """
    Spend credits atomically using SQLAlchemy
    Returns new balance or raises exception
    """
    try:
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        current_balance = user.mini_word_credits or 0

        if current_balance < amount:
            raise ValueError("INSUFFICIENT_CREDITS")

        new_balance = current_balance - amount
        user.mini_word_credits = new_balance

        db.session.commit()
        current_app.logger.info(f"User {user_id} spent {amount} credits for {reason}. New balance: {new_balance}")

        return new_balance

    except Exception as e:
        db.session.rollback()
        if "INSUFFICIENT_CREDITS" in str(e):
            raise ValueError("INSUFFICIENT_CREDITS")
        else:
            current_app.logger.error(f"Database error spending credits: {e}")
            raise ValueError(f"Database error: {e}")

def add_credits(user_id, amount, reason="purchase"):
    """
    Add credits to user's balance (for purchases)
    Returns new balance
    """
    try:
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        current_balance = user.mini_word_credits or 0
        new_balance = current_balance + amount
        user.mini_word_credits = new_balance

        db.session.commit()
        current_app.logger.info(f"User {user_id} gained {amount} credits for {reason}. New balance: {new_balance}")

        return new_balance

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding credits: {e}")
        raise

@credits_bp.route("/test-spend", methods=["POST"])
@require_csrf
def test_spend():
    """Test endpoint for spending credits (development only)"""
    if not current_app.debug:
        abort(404)

    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json() or {}
    amount = int(data.get('amount', 1))
    reason = data.get('reason', 'test')

    try:
        new_balance = spend_credits(user_id, amount, reason)
        return jsonify({
            "ok": True,
            "new_balance": new_balance,
            "spent": amount,
            "reason": reason
        })
    except ValueError as e:
        if "INSUFFICIENT_CREDITS" in str(e):
            return jsonify({"ok": False, "error": "INSUFFICIENT_CREDITS"}), 402
        else:
            return jsonify({"error": str(e)}), 500

@credits_bp.route("/test-add", methods=["POST"])
@require_csrf
def test_add():
    """Test endpoint for adding credits (development only)"""
    if not current_app.debug:
        abort(404)

    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json() or {}
    amount = int(data.get('amount', 10))
    reason = data.get('reason', 'test_add')

    try:
        new_balance = add_credits(user_id, amount, reason)
        return jsonify({
            "ok": True,
            "new_balance": new_balance,
            "added": amount,
            "reason": reason
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500