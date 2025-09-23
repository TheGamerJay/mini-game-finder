# wsgi.py - Proper import for Railway deployment
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app instance directly from app.py
from app import app

if __name__ == "__main__":
    app.run()