#!/usr/bin/env python3

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User

def check_and_fix_riddle_migration():
    app = create_app()

    with app.app_context():
        try:
            # Try to query the riddles_played_free column
            users = User.query.limit(1).all()
            if users:
                user = users[0]
                riddles_played = getattr(user, 'riddles_played_free', None)
                print(f"✅ riddles_played_free column exists. Sample value: {riddles_played}")
                return True
        except Exception as e:
            print(f"❌ riddles_played_free column missing or error: {e}")

            # Apply the migration
            try:
                print("🔧 Applying riddles_played_free migration...")
                db.engine.execute('ALTER TABLE users ADD COLUMN riddles_played_free INTEGER DEFAULT 0 NOT NULL')
                db.session.commit()
                print("✅ Migration applied successfully!")
                return True
            except Exception as migrate_error:
                print(f"❌ Failed to apply migration: {migrate_error}")
                return False

if __name__ == "__main__":
    check_and_fix_riddle_migration()