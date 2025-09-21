# wsgi.py
import sys
import os

# Railway creates /app/app/__init__.py which conflicts with our app.py
# We need to import from the correct location
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    # Try importing from root app.py first
    if os.path.exists(os.path.join(current_dir, 'app.py')):
        import importlib.util
        spec = importlib.util.spec_from_file_location("app", os.path.join(current_dir, 'app.py'))
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)
        app = app_module.app
    else:
        # Fallback to regular import
        from app import app
except Exception as e:
    print(f"Import error: {e}")
    # Last resort - try direct execution
    exec(open(os.path.join(current_dir, 'app.py')).read())
    app = locals()['app']