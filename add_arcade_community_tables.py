#!/usr/bin/env python3
"""
Add community-based arcade game tables for enhanced leaderboards
"""
import os
import psycopg2
from psycopg2.extras import DictCursor

def get_db_connection():
    """Get database connection from DATABASE_URL"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Handle Heroku postgres:// URLs
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(
        database_url,
        sslmode='require',
        cursor_factory=DictCursor
    )
    return conn

def main():
    print("🎮 Adding arcade community tables...")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if we need to create a default community
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'communities'")
        has_communities = cursor.fetchone()[0] > 0

        if not has_communities:
            print("Creating communities table...")
            cursor.execute("""
                CREATE TABLE communities (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    is_default BOOLEAN DEFAULT FALSE
                );
            """)

            # Insert default community
            cursor.execute("""
                INSERT INTO communities (name, description, is_default)
                VALUES ('Mini Word Finder', 'Default community for all players', TRUE);
            """)
            print("✅ Communities table created with default community")

        # Check if community_members exists
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'community_members'")
        has_members = cursor.fetchone()[0] > 0

        if not has_members:
            print("Creating community_members table...")
            cursor.execute("""
                CREATE TABLE community_members (
                    community_id INTEGER REFERENCES communities(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    joined_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (community_id, user_id)
                );
            """)
            print("✅ Community members table created")

        # Check if enhanced game_profile exists
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'game_profile'")
        has_profiles = cursor.fetchone()[0] > 0

        if not has_profiles:
            print("Creating enhanced game_profile table...")
            cursor.execute("""
                CREATE TABLE game_profile (
                    community_id INTEGER REFERENCES communities(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    game_code VARCHAR(10) NOT NULL,
                    plays INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    free_remaining INTEGER DEFAULT 5,
                    last_play_at TIMESTAMP,
                    last_win_at TIMESTAMP,
                    PRIMARY KEY (community_id, user_id, game_code)
                );
            """)

            cursor.execute("CREATE INDEX idx_game_profile_wins ON game_profile (community_id, game_code, wins DESC);")
            print("✅ Enhanced game_profile table created")
        else:
            # Check if we need to add community_id column to existing table
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'game_profile' AND column_name = 'community_id'
            """)
            has_community_id = cursor.fetchone() is not None

            if not has_community_id:
                print("Adding community_id to existing game_profile table...")
                cursor.execute("ALTER TABLE game_profile ADD COLUMN community_id INTEGER DEFAULT 1;")
                cursor.execute("UPDATE game_profile SET community_id = 1 WHERE community_id IS NULL;")
                cursor.execute("ALTER TABLE game_profile ALTER COLUMN community_id SET NOT NULL;")
                cursor.execute("ALTER TABLE game_profile ADD FOREIGN KEY (community_id) REFERENCES communities(id);")

                # Recreate primary key with community_id
                cursor.execute("ALTER TABLE game_profile DROP CONSTRAINT IF EXISTS game_profile_pkey;")
                cursor.execute("ALTER TABLE game_profile ADD PRIMARY KEY (community_id, user_id, game_code);")
                print("✅ Enhanced existing game_profile table with community support")

        # Check if game_results exists (for time-windowed leaderboards)
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'game_results'")
        has_results = cursor.fetchone()[0] > 0

        if not has_results:
            print("Creating game_results table for time-windowed leaderboards...")
            cursor.execute("""
                CREATE TABLE game_results (
                    id SERIAL PRIMARY KEY,
                    community_id INTEGER REFERENCES communities(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    game_code VARCHAR(10) NOT NULL,
                    won BOOLEAN NOT NULL,
                    played_at TIMESTAMP DEFAULT NOW()
                );
            """)

            cursor.execute("CREATE INDEX idx_game_results_time ON game_results (community_id, game_code, played_at DESC);")
            cursor.execute("CREATE INDEX idx_game_results_wins ON game_results (community_id, game_code, won, played_at DESC);")
            print("✅ Game results table created for time-windowed tracking")

        # Create leaderboard views for better performance
        print("Creating leaderboard views...")
        cursor.execute("""
            CREATE OR REPLACE VIEW v_leaderboard_alltime AS
            SELECT
                community_id,
                user_id,
                SUM(wins) as total_wins,
                SUM(plays) as total_plays,
                MAX(last_win_at) as last_win_at
            FROM game_profile
            GROUP BY community_id, user_id;
        """)

        # Check if apply_credit_delta function exists or create a simple version
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.routines
            WHERE routine_name = 'apply_credit_delta'
        """)
        has_credit_function = cursor.fetchone()[0] > 0

        if not has_credit_function:
            print("Creating apply_credit_delta function...")
            cursor.execute("""
                CREATE OR REPLACE FUNCTION apply_credit_delta(
                    p_user_id INTEGER,
                    p_delta INTEGER,
                    p_reason TEXT,
                    p_ref_id TEXT DEFAULT NULL,
                    p_community_id INTEGER DEFAULT 1
                ) RETURNS INTEGER AS $$
                DECLARE
                    current_credits INTEGER;
                    new_credits INTEGER;
                BEGIN
                    -- Get current credits
                    SELECT mini_word_credits INTO current_credits FROM users WHERE id = p_user_id;

                    IF current_credits IS NULL THEN
                        RAISE EXCEPTION 'User not found';
                    END IF;

                    new_credits := current_credits + p_delta;

                    IF new_credits < 0 THEN
                        RAISE EXCEPTION 'INSUFFICIENT_CREDITS';
                    END IF;

                    -- Update user credits
                    UPDATE users SET mini_word_credits = new_credits WHERE id = p_user_id;

                    -- Insert into credit transactions if table exists
                    INSERT INTO credit_txns (user_id, amount, reason, created_at)
                    VALUES (p_user_id, p_delta, p_reason, NOW())
                    ON CONFLICT DO NOTHING;

                    RETURN new_credits;
                END;
                $$ LANGUAGE plpgsql;
            """)
            print("✅ Credit delta function created")

        conn.commit()
        print("🎉 All arcade community tables and functions created successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()