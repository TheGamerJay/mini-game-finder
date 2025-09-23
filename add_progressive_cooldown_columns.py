#!/usr/bin/env python3
"""
Add progressive cooldown columns to user_community_stats table
"""

import sqlite3
import os

def add_progressive_cooldown_columns():
    """Add the new columns for progressive cooldown tracking"""
    try:
        # Connect to local database
        conn = sqlite3.connect('instance/local.db')
        cur = conn.cursor()

        print("ADDING PROGRESSIVE COOLDOWN COLUMNS")
        print("=" * 40)

        # Check if columns already exist
        cur.execute("PRAGMA table_info(user_community_stats)")
        existing_columns = [col[1] for col in cur.fetchall()]

        print("Existing columns:", existing_columns)

        # Add recent_actions_hour column if it doesn't exist
        if 'recent_actions_hour' not in existing_columns:
            print("Adding recent_actions_hour column...")
            cur.execute("""
                ALTER TABLE user_community_stats
                ADD COLUMN recent_actions_hour INTEGER DEFAULT 0 NOT NULL
            """)
            print("SUCCESS: recent_actions_hour column added")
        else:
            print("OK: recent_actions_hour column already exists")

        # Add recent_actions_reset_at column if it doesn't exist
        if 'recent_actions_reset_at' not in existing_columns:
            print("Adding recent_actions_reset_at column...")
            cur.execute("""
                ALTER TABLE user_community_stats
                ADD COLUMN recent_actions_reset_at DATETIME
            """)
            print("SUCCESS: recent_actions_reset_at column added")
        else:
            print("OK: recent_actions_reset_at column already exists")

        conn.commit()

        # Verify the changes
        cur.execute("PRAGMA table_info(user_community_stats)")
        new_columns = [col[1] for col in cur.fetchall()]
        print("\nUpdated columns:", new_columns)

        print("\nSUCCESS: Progressive cooldown columns added")

        conn.close()
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    add_progressive_cooldown_columns()