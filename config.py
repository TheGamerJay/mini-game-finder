# config.py - Centralized configuration
"""
Centralized configuration for Mini Game Finder
"""

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "core.index",           # Home page (/)
    "version",              # /_version endpoint
    "health",               # /_health endpoint
    "readiness",            # /_readiness endpoint
    "debug_env",            # /_debug/env endpoint (for security audit)
    "core.login",           # Login page
    "core.register",        # Register page
    "core.reset_request",   # Password reset request
    "core.reset_token",     # Password reset with token
    "health",               # Health check (/_health)
    "core.terms",           # Terms of service
    "core.policy",          # Privacy policy
    "core.privacy",         # Privacy page
    "static",               # Static files
}

# Import auth utilities
from utils.auth import public_route