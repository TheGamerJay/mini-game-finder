# utils/auth.py - Authentication utilities
"""
Centralized authentication utilities for Mini Game Finder
"""
from flask import request, redirect, url_for, jsonify, current_app
from flask_login import current_user
import os


def public_route(view):
    """
    Decorator to mark a route as public (no auth required)

    Usage:
        @public_route
        @bp.route("/terms")
        def terms():
            return render_template("terms.html")
    """
    view._public = True
    return view


def is_api_path(path=None):
    """Check if the current request path is an API endpoint"""
    if path is None:
        path = request.path or ""
    return path.startswith("/api/") or path.startswith("/game/api/")


def require_auth_json():
    """
    Helper for API endpoints that need auth.
    Returns 401 JSON if not authenticated, None if authenticated.

    Usage:
        def api_endpoint():
            auth_error = require_auth_json()
            if auth_error:
                return auth_error
            # ... rest of API logic
    """
    if not current_user.is_authenticated:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    return None


def get_user_safe():
    """
    Safely get current user, returns None if not authenticated.
    Use this instead of accessing current_user directly in views that
    might be called without authentication.
    """
    return current_user if current_user.is_authenticated else None


def minimal_auth_guard():
    """
    Minimal auth guard implementation for app-level before_request.
    Can be used as a drop-in replacement for complex auth logic.
    """
    from config import PUBLIC_ENDPOINTS

    # Debug logging (only in debug mode)
    if os.getenv("APP_DEBUG") == "1":
        print(f"[AUTH DEBUG] -> {request.endpoint!r} for path {request.path!r}")

    # Emergency auth bypass (only for debugging, unset in production)
    if os.getenv("DISABLE_AUTH") == "1":
        print("[WARNING] Auth disabled via DISABLE_AUTH=1 - DO NOT USE IN PRODUCTION")
        return

    endpoint = request.endpoint or ""

    # Allow static files and public endpoints
    if endpoint.startswith("static") or endpoint in PUBLIC_ENDPOINTS:
        return

    # Check if the view is explicitly marked public
    view = current_app.view_functions.get(request.endpoint)
    if view and getattr(view, "_public", False):
        return

    # Allow authenticated users
    from app import is_user_authenticated
    if is_user_authenticated():
        return

    # Block unauthenticated access: API endpoints get JSON 401, others redirect
    if is_api_path():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    # Non-API pages: redirect to login
    if request.method == "GET":
        return redirect(url_for("core.login", next=request.full_path))
    return jsonify({"error": "unauthorized"}), 401