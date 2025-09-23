#!/usr/bin/env python3
"""
Quick script to reset all game counters to default values
"""

from main import create_app
from models import db, User
import os
import psycopg2
import psycopg2.extras

def reset_counters():
    """Reset all game counters"""
    app = create_app()

    with app.app_context():
        # Get PostgreSQL connection for arcade games
        dsn = os.environ.get("DATABASE_URL")
        if dsn:
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)

            try:
                conn = psycopg2.connect(dsn, sslmode="require", cursor_factory=psycopg2.extras.DictCursor)

                with conn.cursor() as cur:
                    # Reset arcade games (tictactoe and connect4)
                    cur.execute("""
                        UPDATE game_profile
                        SET free_remaining = 5
                        WHERE game_code IN ('ttt', 'c4')
                    """)
                    arcade_reset = cur.rowcount
                    print(f"✅ Reset {arcade_reset} arcade game profiles")

                conn.commit()
                conn.close()

            except Exception as e:
                print(f"❌ Error resetting arcade games: {e}")

        # Reset game finder games using SQLAlchemy
        try:
            # Check what columns exist
            columns = [column.name for column in User.__table__.columns]
            print(f"User table columns: {[col for col in columns if 'free' in col.lower()]}")

            if hasattr(User, 'free_games_used'):
                User.query.update({User.free_games_used: 0})
                print("✅ Reset game finder free_games_used to 0")
            elif hasattr(User, 'free_games_remaining'):
                User.query.update({User.free_games_remaining: 5})
                print("✅ Reset game finder free_games_remaining to 5")
            else:
                print("ℹ️ No game finder free games column found")

            db.session.commit()

        except Exception as e:
            print(f"❌ Error resetting game finder: {e}")
            db.session.rollback()

    print("🎮 Game counter reset complete!")

if __name__ == "__main__":
    reset_counters()