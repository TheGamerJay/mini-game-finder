from flask import Blueprint, jsonify, session
from flask_login import current_user

bp = Blueprint("diag_auth", __name__, url_prefix="/__diag")

@bp.get("/whoami")
def whoami():
    # Check both Flask-Login and session-based authentication
    flask_login_auth = current_user.is_authenticated
    session_auth = session.get('user_id') is not None

    # User is authenticated if either method reports they are
    is_authenticated = flask_login_auth or session_auth

    if not is_authenticated:
        # 200 on purpose to avoid noisy 401 in console
        resp = jsonify({"ok": True, "authenticated": False})
        resp.headers['Cache-Control'] = 'no-store'
        return resp, 200

    # Get user ID from whichever auth method is active
    if flask_login_auth:
        user_id = current_user.get_id()
        email = getattr(current_user, "email", None)
    else:
        user_id = str(session.get('user_id'))
        email = None  # Session doesn't store email

    resp = jsonify({
        "ok": True,
        "authenticated": True,
        "user_id": user_id,
        "email": email,
        "auth_method": "flask_login" if flask_login_auth else "session"
    })
    resp.headers['Cache-Control'] = 'no-store'
    return resp, 200