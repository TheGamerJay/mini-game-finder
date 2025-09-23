#!/usr/bin/env python3
"""
Simple column checker for progressive cooldown
"""

import sqlite3
import os

def check_local_database():
    """Check local SQLite database for progressive cooldown columns"""
    try:
        conn = sqlite3.connect('instance/local.db')
        cur = conn.cursor()

        print("CHECKING LOCAL DATABASE COLUMNS")
        print("=" * 40)

        # Check if table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_community_stats'")
        if not cur.fetchone():
            print("ERROR: user_community_stats table does not exist")
            return False

        # Get all columns
        cur.execute("PRAGMA table_info(user_community_stats)")
        columns = cur.fetchall()

        print("ALL COLUMNS:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

        # Check specifically for progressive cooldown columns
        column_names = [col[1] for col in columns]

        print("\nPROGRESSIVE COOLDOWN COLUMNS:")
        if 'recent_actions_hour' in column_names:
            print("  [OK] recent_actions_hour")
        else:
            print("  [MISSING] recent_actions_hour")

        if 'recent_actions_reset_at' in column_names:
            print("  [OK] recent_actions_reset_at")
        else:
            print("  [MISSING] recent_actions_reset_at")

        # Check basic required columns
        required = ['user_id', 'posts_today', 'reactions_today', 'last_post_at', 'last_reaction_at']
        print("\nBASIC COLUMNS:")
        for req in required:
            if req in column_names:
                print(f"  [OK] {req}")
            else:
                print(f"  [MISSING] {req}")

        conn.close()

        has_progressive = 'recent_actions_hour' in column_names and 'recent_actions_reset_at' in column_names
        has_basic = all(req in column_names for req in required)

        print("\nSUMMARY:")
        print(f"  Basic columns: {'OK' if has_basic else 'MISSING'}")
        print(f"  Progressive cooldown: {'OK' if has_progressive else 'MISSING'}")

        return has_basic and has_progressive

    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    check_local_database()