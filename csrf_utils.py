# csrf_utils.py
from functools import wraps
from flask import request, session, jsonify, current_app
from typing import Optional
import secrets

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Path allowlist for unauthenticated or public endpoints
CSRF_PATH_ALLOWLIST = {
    "/login",
    "/register",
    "/api/login",
    "/api/register",
    "/__csp-report",
    "/stripe/webhook",
}

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

def valid_csrf() -> bool:
    """Public helper to check CSRF validity."""
    return _valid_csrf()

def csrf_exempt(view):
    """Mark a view as CSRF-exempt (used by global before_request)."""
    view._csrf_exempt = True
    return view

def _is_view_exempt() -> bool:
    ep = request.endpoint
    if not ep:
        return False
    view = current_app.view_functions.get(ep)
    return bool(getattr(view, "_csrf_exempt", False))

def should_enforce_csrf() -> bool:
    """Return True if the current request should be CSRF-checked globally."""
    if request.method not in UNSAFE_METHODS:
        return False
    # Path allowlist
    try:
        path = request.path or ""
    except Exception:
        path = ""
    if path in CSRF_PATH_ALLOWLIST:
        return False
    # View-level exemption
    if _is_view_exempt():
        return False
    # Only enforce when we actually have a session token to check
    return "csrf_token" in session

def ensure_csrf_or_403() -> Optional[tuple]:
    """Return a (response, status) tuple if CSRF fails, else None."""
    if valid_csrf():
        return None
    return jsonify(ok=False, error="CSRF_FAILED"), 403

def require_csrf(view):
    """Decorator to require valid CSRF token for state-changing endpoints"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if _valid_csrf():
            return view(*args, **kwargs)
        return jsonify(ok=False, error="CSRF_FAILED"), 403
    return wrapper