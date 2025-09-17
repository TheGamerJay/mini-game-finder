# 🐍 Block B — Flask blueprints: Credits API
# This blueprint handles credit balance and spending operations

from flask import Blueprint, request, jsonify, abort, session, current_app
from models import db, User
from routes import get_session_user
from csrf_utils import require_csrf
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from urllib.parse import urlparse

credits_bp = Blueprint("credits", __name__, url_prefix="/api/credits")

def _get_db_connection():
    """Get raw database connection for credit operations"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not configured")

    url = urlparse(database_url)
    return psycopg2.connect(
        host=url.hostname,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.path[1:]  # Remove leading slash
    )

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
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Use the helper function we created in the migration
                cur.execute("SELECT get_user_credits(%s) AS balance", (user_id,))
                row = cur.fetchone()
                balance = row["balance"] if row else 0

        return jsonify({
            "ok": True,
            "balance": balance,
            "user_id": user_id
        })

    except Exception as e:
        current_app.logger.error(f"Error getting credit balance for user {user_id}: {e}")
        return jsonify({"error": "Failed to get balance"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

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
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        id, reason, amount, puzzle_id, word_id,
                        before_balance, after_balance, created_at
                    FROM credit_usage
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (user_id, limit, offset))

                records = cur.fetchall()

                # Get total count for pagination
                cur.execute("SELECT COUNT(*) FROM credit_usage WHERE user_id = %s", (user_id,))
                total_count = cur.fetchone()["count"]

        return jsonify({
            "ok": True,
            "history": [dict(record) for record in records],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_more": offset + limit < total_count
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error getting credit history for user {user_id}: {e}")
        return jsonify({"error": "Failed to get history"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

def spend_credits(user_id, amount, reason, puzzle_id=None, word_id=None):
    """
    Spend credits atomically using the PostgreSQL function
    Returns new balance or raises exception
    """
    conn = _get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Use the atomic spend function from our migration
                cur.execute("""
                    SELECT spend_user_credits(%s, %s, %s, %s, %s) AS new_balance
                """, (user_id, amount, reason, puzzle_id, word_id))

                result = cur.fetchone()
                new_balance = result["new_balance"]

                # Also update the users table for compatibility
                cur.execute("""
                    UPDATE users SET mini_word_credits = %s WHERE id = %s
                """, (new_balance, user_id))

                return new_balance

    except psycopg2.Error as e:
        if "INSUFFICIENT_CREDITS" in str(e):
            raise ValueError("INSUFFICIENT_CREDITS")
        else:
            current_app.logger.error(f"Database error spending credits: {e}")
            raise ValueError(f"Database error: {e}")
    finally:
        conn.close()

def add_credits(user_id, amount, reason="purchase"):
    """
    Add credits to user's balance (for purchases)
    Returns new balance
    """
    conn = _get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get current balance with lock
                cur.execute("""
                    SELECT balance FROM user_credits
                    WHERE user_id = %s FOR UPDATE
                """, (user_id,))

                row = cur.fetchone()
                if not row:
                    # Create user_credits record if it doesn't exist
                    cur.execute("""
                        INSERT INTO user_credits (user_id, balance)
                        VALUES (%s, %s) RETURNING balance
                    """, (user_id, amount))
                    new_balance = cur.fetchone()["balance"]
                else:
                    current_balance = row["balance"]
                    new_balance = current_balance + amount

                    # Update balance
                    cur.execute("""
                        UPDATE user_credits
                        SET balance = %s, updated_at = now()
                        WHERE user_id = %s
                    """, (new_balance, user_id))

                # Also update the users table for compatibility
                cur.execute("""
                    UPDATE users SET mini_word_credits = %s WHERE id = %s
                """, (new_balance, user_id))

                return new_balance

    except Exception as e:
        current_app.logger.error(f"Error adding credits: {e}")
        raise
    finally:
        conn.close()

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