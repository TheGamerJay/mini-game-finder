#!/usr/bin/env python3
"""Run database migration for daily plays quota system"""

import sqlite3
import os

def run_migration():
    db_path = "instance/local.db"

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Create daily_plays table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_plays (
              user_id   INTEGER NOT NULL,
              game_key  TEXT    NOT NULL,
              day_utc   DATE    NOT NULL,
              used      INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (user_id, game_key, day_utc)
            )
        """)

        # Try to add missing columns (will silently fail if columns exist)
        try:
            cursor.execute("ALTER TABLE credit_txns ADD COLUMN idempotency_key VARCHAR(64)")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE scores ADD COLUMN duration_sec INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists

        conn.commit()
        print("Migration completed successfully")

if __name__ == "__main__":
    run_migration()