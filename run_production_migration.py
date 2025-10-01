#!/usr/bin/env python3
"""
Production migration runner for Railway deployment.
Runs the critical database fixes to resolve post_reactions.id column issues.
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _normalize_db_url(url: str | None) -> str | None:
    """Normalize database URL for SQLAlchemy compatibility"""
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

def run_migration():
    """Run the database migration"""
    try:
        # Get database URL from environment
        database_url = _normalize_db_url(os.getenv("DATABASE_URL"))
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return False

        logger.info("Connecting to production database...")

        # Create engine with connection pooling
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=1800
        )

        # Execute migration
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Running post_reactions table migration...")

                # Migration SQL - add missing id column and constraints
                migration_sql = """
                -- Add id column if it doesn't exist
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'post_reactions'
                        AND column_name = 'id'
                    ) THEN
                        ALTER TABLE post_reactions ADD COLUMN id BIGSERIAL;
                        RAISE NOTICE 'Added id column to post_reactions table';
                    END IF;
                END $$;

                -- Update primary key constraints
                DO $$
                BEGIN
                    -- Drop existing primary key if it exists
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.table_constraints
                        WHERE table_name = 'post_reactions'
                        AND constraint_type = 'PRIMARY KEY'
                    ) THEN
                        ALTER TABLE post_reactions DROP CONSTRAINT post_reactions_pkey;
                        RAISE NOTICE 'Dropped existing primary key constraint';
                    END IF;

                    -- Add new primary key on id column
                    ALTER TABLE post_reactions ADD CONSTRAINT post_reactions_pkey PRIMARY KEY (id);
                    RAISE NOTICE 'Added primary key constraint on id column';
                END $$;

                -- Ensure unique constraint on (post_id, user_id)
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.table_constraints
                        WHERE constraint_name = 'uq_post_user'
                        AND table_name = 'post_reactions'
                    ) THEN
                        ALTER TABLE post_reactions
                        ADD CONSTRAINT uq_post_user
                        UNIQUE (post_id, user_id);
                        RAISE NOTICE 'Added unique constraint uq_post_user';
                    END IF;
                END $$;

                -- Ensure reaction_type has proper default and NOT NULL
                DO $$
                BEGIN
                    -- Set default value
                    ALTER TABLE post_reactions ALTER COLUMN reaction_type SET DEFAULT 'love';

                    -- Update any NULL values
                    UPDATE post_reactions SET reaction_type = 'love' WHERE reaction_type IS NULL;

                    -- Make NOT NULL
                    ALTER TABLE post_reactions ALTER COLUMN reaction_type SET NOT NULL;

                    RAISE NOTICE 'Set reaction_type constraints';
                END $$;

                -- Ensure created_at column exists
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'post_reactions'
                        AND column_name = 'created_at'
                    ) THEN
                        ALTER TABLE post_reactions ADD COLUMN created_at TIMESTAMP DEFAULT NOW();
                        RAISE NOTICE 'Added created_at column';
                    END IF;
                END $$;
                """

                # Execute the migration
                conn.execute(text(migration_sql))
                trans.commit()

                logger.info("✅ Post reactions migration completed successfully!")

                # Fix users email nulls
                logger.info("Running users email null fix...")
                with engine.connect() as conn2:
                    trans2 = conn2.begin()
                    try:
                        email_fix_sql = """
                        -- Update null email addresses
                        UPDATE users
                        SET email = 'user_' || id || '@noemail.placeholder'
                        WHERE email IS NULL;

                        -- Ensure email column is NOT NULL
                        DO $$
                        BEGIN
                            ALTER TABLE users ALTER COLUMN email SET NOT NULL;
                            RAISE NOTICE 'Set email column to NOT NULL';
                        END $$;
                        """

                        conn2.execute(text(email_fix_sql))
                        trans2.commit()
                        logger.info("✅ Users email null fix completed successfully!")

                    except Exception as e:
                        trans2.rollback()
                        logger.warning(f"Users email fix failed (non-critical): {e}")

                # Create user_community_stats table if missing
                logger.info("Checking user_community_stats table...")
                with engine.connect() as conn3:
                    trans3 = conn3.begin()
                    try:
                        community_stats_sql = """
                        -- Create user_community_stats table if it doesn't exist
                        CREATE TABLE IF NOT EXISTS user_community_stats (
                            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                            posts_today INTEGER NOT NULL DEFAULT 0,
                            reactions_today INTEGER NOT NULL DEFAULT 0,
                            reports_today INTEGER NOT NULL DEFAULT 0,
                            last_post_at TIMESTAMP,
                            last_reaction_at TIMESTAMP,
                            last_report_at TIMESTAMP,
                            last_reset_date DATE DEFAULT CURRENT_DATE,
                            total_posts INTEGER NOT NULL DEFAULT 0,
                            total_reactions_given INTEGER NOT NULL DEFAULT 0,
                            total_reactions_received INTEGER NOT NULL DEFAULT 0,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP
                        );
                        """

                        conn3.execute(text(community_stats_sql))
                        trans3.commit()
                        logger.info("✅ user_community_stats table verified/created successfully!")

                    except Exception as e:
                        trans3.rollback()
                        logger.warning(f"user_community_stats table creation failed (non-critical): {e}")

                # Fix scores table - add missing columns
                logger.info("Fixing scores table columns...")
                with engine.connect() as conn4:
                    trans4 = conn4.begin()
                    try:
                        scores_fix_sql = """
                        -- Add found_count column if missing
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'scores' AND column_name = 'found_count'
                            ) THEN
                                ALTER TABLE scores ADD COLUMN found_count INTEGER DEFAULT 0;
                                RAISE NOTICE 'Added found_count column to scores';
                            END IF;
                        END $$;

                        -- Add total_words column if missing
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'scores' AND column_name = 'total_words'
                            ) THEN
                                ALTER TABLE scores ADD COLUMN total_words INTEGER DEFAULT 0;
                                RAISE NOTICE 'Added total_words column to scores';
                            END IF;
                        END $$;

                        -- Add points column if missing
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'scores' AND column_name = 'points'
                            ) THEN
                                ALTER TABLE scores ADD COLUMN points INTEGER DEFAULT 0;
                                RAISE NOTICE 'Added points column to scores';
                            END IF;
                        END $$;

                        -- Add duration_sec column if missing
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'scores' AND column_name = 'duration_sec'
                            ) THEN
                                ALTER TABLE scores ADD COLUMN duration_sec INTEGER DEFAULT 0;
                                RAISE NOTICE 'Added duration_sec column to scores';
                            END IF;
                        END $$;
                        """

                        conn4.execute(text(scores_fix_sql))
                        trans4.commit()
                        logger.info("✅ Scores table columns fixed successfully!")

                    except Exception as e:
                        trans4.rollback()
                        logger.warning(f"Scores table fix failed (non-critical): {e}")

                return True

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration failed: {e}")
                return False

    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting production database migration...")

    success = run_migration()

    if success:
        logger.info("🎉 All migrations completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Migration failed!")
        sys.exit(1)