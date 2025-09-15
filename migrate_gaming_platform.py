#!/usr/bin/env python3
"""
Gaming Platform Migration - Add all tables and columns for the comprehensive system
"""
from app import app
from models import db
from sqlalchemy import text

def migrate_gaming_platform():
    """Add all new tables and columns for the gaming platform"""

    with app.app_context():
        try:
            print("Starting Gaming Platform Migration...")

            # 1. Add credits and war_wins to users table
            print("Adding user credits and war wins...")
            try:
                db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS mini_word_credits INTEGER NOT NULL DEFAULT 0'))
                db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS war_wins INTEGER NOT NULL DEFAULT 0'))
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
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        kind VARCHAR(40) NOT NULL,
                        amount_delta INTEGER NOT NULL,
                        amount_usd NUMERIC(8,2),
                        ref_code VARCHAR(64),
                        meta_json JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
                db.session.execute(text('ALTER TABLE posts ADD COLUMN IF NOT EXISTS boost_score INTEGER NOT NULL DEFAULT 0'))
                db.session.execute(text('ALTER TABLE posts ADD COLUMN IF NOT EXISTS last_boost_at TIMESTAMPTZ'))
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
                        id BIGSERIAL PRIMARY KEY,
                        post_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        credits_spent INTEGER NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
                        id BIGSERIAL PRIMARY KEY,
                        challenger_user_id BIGINT NOT NULL,
                        challenger_post_id BIGINT,
                        challenged_user_id BIGINT NOT NULL,
                        challenged_post_id BIGINT,
                        status VARCHAR(16) NOT NULL DEFAULT 'pending',
                        starts_at TIMESTAMPTZ,
                        ends_at TIMESTAMPTZ,
                        winner_user_id BIGINT,
                        challenger_final_score INTEGER,
                        challenged_final_score INTEGER,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
                        id BIGSERIAL PRIMARY KEY,
                        war_id BIGINT NOT NULL,
                        actor_user_id BIGINT NOT NULL,
                        target_post_id BIGINT NOT NULL,
                        action VARCHAR(16) NOT NULL,
                        credits_spent INTEGER NOT NULL,
                        points_delta INTEGER NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        code VARCHAR(64) NOT NULL,
                        level INTEGER NOT NULL DEFAULT 1,
                        awarded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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
    migrate_gaming_platform()