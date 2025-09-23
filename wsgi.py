# wsgi.py - Railway deployment with ProxyFix
import os
import sys
from werkzeug.middleware.proxy_fix import ProxyFix

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app from app.py
from app import create_app

# Create the app
app = create_app()

# Add ProxyFix for Railway proxy handling
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Ensure proper HTTPS and session config for Railway
app.config.update(
    PREFERRED_URL_SCHEME="https",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
)