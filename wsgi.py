# wsgi.py
# Robust loader: works with different project structures
try:
    # Try root-level app.py with create_app factory
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    import app as app_module
    if hasattr(app_module, 'create_app'):
        app = app_module.create_app()
    elif hasattr(app_module, 'app'):
        app = app_module.app
    else:
        raise ImportError("No Flask app found")
except (ImportError, AttributeError):
    try:
        # Fallback: try package-style import
        from app import create_app  # type: ignore
        app = create_app()
    except (ImportError, AttributeError):
        try:
            from app import app as app  # type: ignore
        except (ImportError, AttributeError):
            # Last resort: direct import
            exec("import app as app_module; app = app_module.app")