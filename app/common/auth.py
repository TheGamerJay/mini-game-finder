"""Authentication utilities for clean architecture."""
from functools import wraps
from typing import Optional, Callable, Any

from flask import request, session
from flask_login import current_user

from app.common.errors import Unauthorized


def current_user_id() -> int:
    """
    Get the current authenticated user's ID.

    Supports both Flask-Login and session-based authentication
    for backward compatibility during migration.

    Returns:
        The authenticated user's ID

    Raises:
        Unauthorized: If no authenticated user is found
    """
    # Try Flask-Login first
    if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
        user_id = current_user.get_id()
        if user_id:
            return int(user_id)

    # Try session-based auth
    session_user_id = session.get("user_id")
    if session_user_id:
        return int(session_user_id)

    # Try header-based auth (for API clients)
    header_user_id = request.headers.get("X-User-Id")
    if header_user_id:
        try:
            return int(header_user_id)
        except ValueError:
            pass

    # No authentication found
    raise Unauthorized("Authentication required")


def current_user_id_optional() -> Optional[int]:
    """
    Get the current user ID without raising an exception if not authenticated.

    Returns:
        The authenticated user's ID, or None if not authenticated
    """
    try:
        return current_user_id()
    except Unauthorized:
        return None


def is_authenticated() -> bool:
    """
    Check if the current request is from an authenticated user.

    Returns:
        True if user is authenticated, False otherwise
    """
    return current_user_id_optional() is not None


def require_auth(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to require authentication for routes.

    Usage:
        @require_auth
        def my_route():
            # route code here
            user_id = request.current_user.id

    The decorator adds a 'current_user' attribute to the request object
    with the authenticated user information.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user_id = current_user_id()
            # Add user info to request for easy access in the route
            request.current_user = type('User', (), {'id': user_id})()
            return f(*args, **kwargs)
        except Unauthorized as e:
            from app.common.http import ApiResponse
            return ApiResponse.error("Authentication required", 401)
    return decorated_function


def require_auth_helper() -> int:
    """
    Helper function to require authentication (non-decorator version).

    Returns:
        The authenticated user's ID

    Raises:
        Unauthorized: If user is not authenticated
    """
    return current_user_id()


def get_user_email() -> Optional[str]:
    """
    Get the current user's email if available.

    Returns:
        User's email address, or None if not available
    """
    if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
        return getattr(current_user, "email", None)
    return None