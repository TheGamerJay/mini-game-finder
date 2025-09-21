import os
import sys

def run_sql_migrations():
    """Run additional SQL migrations that SQLAlchemy might miss"""
    try:
        from sqlalchemy import create_engine, text

        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return

        engine = create_engine(database_url)

        # Read and run production column fixes
        production_sql_path = os.path.join(os.path.dirname(__file__), 'fix_production_columns.sql')
        if os.path.exists(production_sql_path):
            print("Running production column fixes...")
            with open(production_sql_path, 'r') as f:
                sql_content = f.read()

            with engine.connect() as conn:
                # Execute the entire SQL script
                conn.execute(text(sql_content))
                conn.commit()
                print("Production column fixes completed")

        # Run post_reactions fix
        post_reactions_sql_path = os.path.join(os.path.dirname(__file__), 'fix_post_reactions_add_id.sql')
        if os.path.exists(post_reactions_sql_path):
            print("Running post_reactions fixes...")
            with open(post_reactions_sql_path, 'r') as f:
                sql_content = f.read()

            with engine.connect() as conn:
                conn.execute(text(sql_content))
                conn.commit()
                print("Post reactions fixes completed")

    except Exception as e:
        print(f"SQL migration error: {e}")
        import traceback
        traceback.print_exc()

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
            print("Database tables created successfully!")

        # Run additional SQL migrations outside of Flask context
        print("Running additional SQL migrations...")
        run_sql_migrations()

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
