#!/usr/bin/env python3

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db
from sqlalchemy import text

def fix_database_schema():
    app = create_app()

    with app.app_context():
        print("Fixing database schema...")

        # List of missing columns to add
        migrations = [
            "ALTER TABLE users ADD COLUMN riddles_played_free INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN welcome_pack_purchased BOOLEAN DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_password_reset_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN password_reset_count INTEGER DEFAULT 0",
            # Individual game counters with daily reset
            "ALTER TABLE users ADD COLUMN wordgame_played_free INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN connect4_played_free INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN tictactoe_played_free INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_free_reset_date DATE"
        ]

        for migration in migrations:
            try:
                print(f"Applying: {migration}")
                db.session.execute(text(migration))
                print("Success")
            except Exception as e:
                print(f"Error: {e}")

        try:
            db.session.commit()
            print("All migrations applied successfully!")
        except Exception as e:
            print(f"Error committing: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_database_schema()