from flask import Flask
import os, secrets

APP_NAME = os.environ.get("APP_NAME", "Mini Word Finder")
SECRET_KEY = os.environ.get("FLASK_SECRET", os.environ.get("SECRET_KEY", secrets.token_hex(32)))

def create_app():
    app = Flask(__name__)
    
    # Set secret key
    app.secret_key = SECRET_KEY
    
    # Basic configuration
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", os.urandom(24)),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10 MB
        ALLOWED_IMAGE_EXTENSIONS={"jpg", "jpeg", "png", "webp"},
        UPLOADS_DIR=os.path.join(app.root_path, "static", "uploads"),
        STORAGE_BACKEND=os.getenv("STORAGE_BACKEND", "local").lower(),
        STARTING_MINI_WORD_CREDITS=int(os.getenv("STARTING_MINI_WORD_CREDITS", "10")),
        
        # Storage config
        S3_ENDPOINT_URL=os.getenv("S3_ENDPOINT_URL", ""),
        S3_REGION=os.getenv("S3_REGION", "us-east-1"),
        S3_BUCKET=os.getenv("S3_BUCKET", ""),
        S3_ACCESS_KEY_ID=os.getenv("S3_ACCESS_KEY_ID", ""),
        S3_SECRET_ACCESS_KEY=os.getenv("S3_SECRET_ACCESS_KEY", ""),
        S3_CDN_BASE_URL=os.getenv("S3_CDN_BASE_URL", ""),
        SUPABASE_URL=os.getenv("SUPABASE_URL", ""),
        SUPABASE_ANON_KEY=os.getenv("SUPABASE_ANON_KEY", ""),
        SUPABASE_BUCKET=os.getenv("SUPABASE_BUCKET", "")
    )

    # Create uploads directory
    os.makedirs(app.config["UPLOADS_DIR"], exist_ok=True)

    # Initialize database
    from models import init_db
    init_db(app, echo=False)
    
    # Register routes
    from routes import register_routes
    register_routes(app)
    
    # Register API routes
    from api_routes import bp as api_bp
    app.register_blueprint(api_bp)
    
    return app

# Create the application instance
app = create_app()
