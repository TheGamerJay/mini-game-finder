# wsgi.py - Simplified for Railway deployment
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Direct execution approach - bypass import system entirely
with open('app.py', 'r') as f:
    code = f.read()

# Execute the app.py code in this namespace
exec(code)

# The app variable should now be available
if 'app' not in locals():
    raise RuntimeError("Flask app not found after executing app.py")