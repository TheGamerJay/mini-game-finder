# wsgi.py
# Robust loader: works with either a factory (create_app/make_app) or a plain `app` object.
try:
    # Preferred: application factory pattern
    from app import create_app  # type: ignore
    app = create_app()
except (ImportError, AttributeError):
    try:
        from app import make_app  # type: ignore
        app = make_app()
    except (ImportError, AttributeError):
        # Fallback: a module-level Flask instance named `app`
        from app import app as app  # type: ignore