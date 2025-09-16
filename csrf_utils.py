# csrf_utils.py
from functools import wraps
from flask import request, session, jsonify
import secrets

def rotate_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    session['csrf_token'] = token
    return token

def clear_csrf_token() -> None:
    session.pop('csrf_token', None)

def _valid_csrf() -> bool:
    sess_token = session.get("csrf_token")
    hdr_token = request.headers.get("X-CSRF-Token")
    return bool(sess_token and hdr_token and sess_token == hdr_token)

def require_csrf(view):
    """Decorator to require valid CSRF token for state-changing endpoints"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if _valid_csrf():
            return view(*args, **kwargs)
        return jsonify(ok=False, error="CSRF_FAILED"), 403
    return wrapper