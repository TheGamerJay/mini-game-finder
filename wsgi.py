# wsgi.py - Proper import using create_app factory
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import using importlib to avoid conflict with app/ directory
import importlib.util
spec = importlib.util.spec_from_file_location("app_module", "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)

# Use the create_app factory
app = app_module.create_app()

if __name__ == "__main__":
    app.run()