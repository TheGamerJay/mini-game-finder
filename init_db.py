import os
import sys

def init_database():
    try:
        print("Starting database initialization...")

        # Check if DATABASE_URL is set
        if not os.environ.get('DATABASE_URL'):
            print("DATABASE_URL not set, skipping database initialization")
            return

        print("Importing Flask app...")
        from app import create_app
        from models import db

        print("Creating app instance...")
        app = create_app()

        print("Entering app context...")
        with app.app_context():
            print("Creating all database tables...")
            # Only create tables, don't drop existing ones
            db.create_all()
            print("Database initialization completed successfully!")

    except Exception as e:
        print(f"Database initialization error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        # Don't exit with error - let the app try to start anyway
        print("Continuing despite database initialization error...")

if __name__ == "__main__":
    init_database()
