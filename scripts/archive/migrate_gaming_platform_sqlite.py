#!/usr/bin/env python3
"""
Gaming Platform Migration for SQLite - Add all tables and columns for the comprehensive system
"""
from app import app
from models import db
from sqlalchemy import text

def migrate_gaming_platform_sqlite():
    """Add all new tables and columns for the gaming platform (SQLite compatible)"""

    with app.app_context():
        try:
            print("Starting Gaming Platform Migration (SQLite)...")

            # 1. Add credits and war_wins to users table
            print("Adding user credits and war wins...")
            try:
                # Check if columns exist first
                result = db.session.execute(text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result.fetchall()]

                if 'mini_word_credits' not in columns:
                    db.session.execute(text('ALTER TABLE users ADD COLUMN mini_word_credits INTEGER NOT NULL DEFAULT 0'))
                    print("Added mini_word_credits column")

                if 'war_wins' not in columns:
                    db.session.execute(text('ALTER TABLE users ADD COLUMN war_wins INTEGER NOT NULL DEFAULT 0'))
                    print("Added war_wins column")

                db.session.commit()
                print("SUCCESS: User credits and war wins added")
            except Exception as e:
                print(f"INFO: User columns: {e}")
                db.session.rollback()

            # 2. Create transactions table
            print("Creating transactions table...")
            try:
                db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS credit_txns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        kind VARCHAR(40) NOT NULL,
                        amount_delta INTEGER NOT NULL,
                        amount_usd REAL,
                        ref_code VARCHAR(64),
                        meta_json TEXT DEFAULT '{}',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                '''))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_tx_user_created ON credit_txns(user_id, created_at DESC)'))
                db.session.commit()
                print("SUCCESS: Transactions table created")
            except Exception as e:
                print(f"INFO: Transactions table: {e}")
                db.session.rollback()

            # 3. Add boost fields to posts
            print("Adding boost fields to posts...")
            try:
                # Check if columns exist first
                result = db.session.execute(text("PRAGMA table_info(posts)"))
                columns = [row[1] for row in result.fetchall()]

                if 'boost_score' not in columns:
                    db.session.execute(text('ALTER TABLE posts ADD COLUMN boost_score INTEGER NOT NULL DEFAULT 0'))
                    print("Added boost_score column")

                if 'last_boost_at' not in columns:
                    db.session.execute(text('ALTER TABLE posts ADD COLUMN last_boost_at DATETIME'))
                    print("Added last_boost_at column")

                db.session.commit()
                print("SUCCESS: Post boost fields added")
            except Exception as e:
                print(f"INFO: Post boost fields: {e}")
                db.session.rollback()

            # 4. Create post_boosts table
            print("Creating post boosts table...")
            try:
                db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS post_boosts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        post_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        credits_spent INTEGER NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                '''))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_post_boosts_post ON post_boosts(post_id)'))
                db.session.commit()
                print("SUCCESS: Post boosts table created")
            except Exception as e:
                print(f"INFO: Post boosts table: {e}")
                db.session.rollback()

            # 5. Create boost_wars table
            print("Creating boost wars table...")
            try:
                db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS boost_wars (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        challenger_user_id INTEGER NOT NULL,
                        challenger_post_id INTEGER,
                        challenged_user_id INTEGER NOT NULL,
                        challenged_post_id INTEGER,
                        status VARCHAR(16) NOT NULL DEFAULT 'pending',
                        starts_at DATETIME,
                        ends_at DATETIME,
                        winner_user_id INTEGER,
                        challenger_final_score INTEGER,
                        challenged_final_score INTEGER,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                '''))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_wars_status ON boost_wars(status, ends_at DESC)'))
                db.session.commit()
                print("SUCCESS: Boost wars table created")
            except Exception as e:
                print(f"INFO: Boost wars table: {e}")
                db.session.rollback()

            # 6. Create boost_war_actions table
            print("Creating boost war actions table...")
            try:
                db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS boost_war_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        war_id INTEGER NOT NULL,
                        actor_user_id INTEGER NOT NULL,
                        target_post_id INTEGER NOT NULL,
                        action VARCHAR(16) NOT NULL,
                        credits_spent INTEGER NOT NULL,
                        points_delta INTEGER NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                '''))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_actions_war ON boost_war_actions(war_id, created_at DESC)'))
                db.session.commit()
                print("SUCCESS: Boost war actions table created")
            except Exception as e:
                print(f"INFO: Boost war actions table: {e}")
                db.session.rollback()

            # 7. Create user_badges table
            print("Creating user badges table...")
            try:
                db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS user_badges (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        code VARCHAR(64) NOT NULL,
                        level INTEGER NOT NULL DEFAULT 1,
                        awarded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (user_id, code)
                    )
                '''))
                db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_badges_code ON user_badges(code, user_id)'))
                db.session.commit()
                print("SUCCESS: User badges table created")
            except Exception as e:
                print(f"INFO: User badges table: {e}")
                db.session.rollback()

            # 8. Give all existing users 100 credits to start
            print("Giving existing users starting credits...")
            try:
                result = db.session.execute(text('UPDATE users SET mini_word_credits = 100 WHERE mini_word_credits = 0'))
                updated = result.rowcount
                db.session.commit()
                print(f"SUCCESS: Gave 100 credits to {updated} existing users")
            except Exception as e:
                print(f"INFO: Starting credits: {e}")
                db.session.rollback()

            print("Gaming Platform Migration completed successfully!")

        except Exception as e:
            print(f"ERROR: Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate_gaming_platform_sqlite()