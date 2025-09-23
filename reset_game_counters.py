#!/usr/bin/env python3
"""
Simple script to reset game counters directly via database
Run this with: python reset_game_counters.py
"""

import os
import sys

# Try to get DATABASE_URL from environment or Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("No DATABASE_URL found. Please set it first:")
    print("export DATABASE_URL='your_database_url_here'")
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 not installed. Installing...")
    os.system("pip install psycopg2-binary")
    import psycopg2
    import psycopg2.extras

def reset_all_counters():
    """Reset all game counters to default values"""

    # Handle Heroku/Railway postgres:// URLs
    dsn = DATABASE_URL
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)

    try:
        conn = psycopg2.connect(dsn, sslmode="require", cursor_factory=psycopg2.extras.DictCursor)

        with conn.cursor() as cur:
            print("Resetting game counters...")

            # Reset arcade games (tic-tac-toe and connect4)
            cur.execute("""
                UPDATE game_profile
                SET free_remaining = 5
                WHERE game_code IN ('ttt', 'c4')
            """)
            arcade_count = cur.rowcount
            print(f"Reset {arcade_count} arcade game profiles to 5 free games")

            # Check and reset game finder games
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name LIKE '%free%'
            """)
            free_columns = [row[0] for row in cur.fetchall()]
            print(f"Found free game columns: {free_columns}")

            if 'free_games_used' in free_columns:
                cur.execute("UPDATE users SET free_games_used = 0")
                word_count = cur.rowcount
                print(f"Reset {word_count} game finder users - free_games_used = 0")
            elif 'free_games_remaining' in free_columns:
                cur.execute("UPDATE users SET free_games_remaining = 5")
                word_count = cur.rowcount
                print(f"Reset {word_count} game finder users - free_games_remaining = 5")
            else:
                print("No game finder free games column found")

            # Reset riddle games if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'riddle_attempts'
                )
            """)
            if cur.fetchone()[0]:
                cur.execute("DELETE FROM riddle_attempts")
                riddle_count = cur.rowcount
                print(f"Reset {riddle_count} riddle attempts")

        conn.commit()
        conn.close()

        print("\nALL GAME COUNTERS RESET SUCCESSFULLY!")
        print("   - Arcade games: 5/5 free plays")
        print("   - Word finder: 0/5 games used")
        print("   - Riddles: Fresh start")

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True

if __name__ == "__main__":
    print("Game Counter Reset Tool")
    print("=" * 30)

    success = reset_all_counters()

    if success:
        print("\nReady to play with fresh counters!")
    else:
        print("\nReset failed - check the error above")
        sys.exit(1)