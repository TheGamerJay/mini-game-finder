# wsgi.py - Railway deployment with ProxyFix
import os
import sys
from werkzeug.middleware.proxy_fix import ProxyFix

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and execute app.py to get the Flask app
import sys
import importlib.util

# Load app.py and execute it to get the app instance
spec = importlib.util.spec_from_file_location("app", "app.py")
app_module = importlib.util.module_from_spec(spec)
sys.modules["app"] = app_module
spec.loader.exec_module(app_module)

# Get the app instance
app = app_module.app

# Add ProxyFix for Railway proxy handling
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Ensure proper HTTPS and session config for Railway
app.config.update(
    PREFERRED_URL_SCHEME="https",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
)