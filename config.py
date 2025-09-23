# config.py - Centralized configuration
"""
Centralized configuration for Mini Game Finder
"""

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "core.index",           # Home page (/)
    "version",              # /_version endpoint
    "core.login",           # Login page
    "core.register",        # Register page
    "core.reset_request",   # Password reset request
    "core.reset_token",     # Password reset with token
    "core.health",          # Health check
    "core.terms",           # Terms of service
    "core.policy",          # Privacy policy
    "core.privacy",         # Privacy page
    "static",               # Static files
}

# Helper decorator to mark routes as public
def public_route(view):
    """Mark a view function as public (no auth required)"""
    view._public = True
    return view