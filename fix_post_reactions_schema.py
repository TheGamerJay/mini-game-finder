#!/usr/bin/env python3
"""
Fix the critical post_reactions.id primary key issue
This is the root cause of cascade delete problems and missing primary key errors
"""

import sqlite3
import os

def fix_post_reactions_schema():
    """Fix the post_reactions table schema"""
    try:
        # Connect to local database
        conn = sqlite3.connect('instance/local.db')
        cur = conn.cursor()

        print("FIXING POST_REACTIONS SCHEMA")
        print("=" * 40)

        # Check current schema
        cur.execute("PRAGMA table_info(post_reactions)")
        current_schema = cur.fetchall()

        print("CURRENT SCHEMA:")
        for col in current_schema:
            print(f"  {col}")

        # Check if id column is primary key
        id_col = [col for col in current_schema if col[1] == 'id'][0]
        is_primary_key = bool(id_col[5])  # pk column in PRAGMA output

        if not is_primary_key:
            print("\nPROBLEM FOUND: id column is not PRIMARY KEY")
            print("FIXING: Recreating table with proper schema...")

            # Create backup table
            cur.execute("""
                CREATE TABLE post_reactions_backup AS
                SELECT * FROM post_reactions
            """)

            # Drop old table
            cur.execute("DROP TABLE post_reactions")

            # Create new table with correct schema
            cur.execute("""
                CREATE TABLE post_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    reaction_type VARCHAR(20) NOT NULL DEFAULT 'love',
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(post_id, user_id)
                )
            """)

            # Restore data (filter out duplicates)
            cur.execute("""
                INSERT INTO post_reactions (post_id, user_id, reaction_type, created_at)
                SELECT DISTINCT post_id, user_id,
                       COALESCE(reaction_type, 'love'),
                       COALESCE(created_at, datetime('now'))
                FROM post_reactions_backup
                WHERE post_id IS NOT NULL AND user_id IS NOT NULL
            """)

            # Drop backup
            cur.execute("DROP TABLE post_reactions_backup")

            conn.commit()

            print("SUCCESS: post_reactions table fixed with proper PRIMARY KEY")

            # Verify fix
            cur.execute("PRAGMA table_info(post_reactions)")
            new_schema = cur.fetchall()

            print("\nNEW SCHEMA:")
            for col in new_schema:
                print(f"  {col}")

        else:
            print("post_reactions.id is already PRIMARY KEY")

        # Check data integrity
        cur.execute("SELECT COUNT(*) FROM post_reactions")
        count = cur.fetchone()[0]
        print(f"\nREACTIONS COUNT: {count}")

        cur.execute("SELECT COUNT(*) FROM (SELECT DISTINCT post_id, user_id FROM post_reactions)")
        unique_count = cur.fetchone()[0]
        print(f"UNIQUE COMBINATIONS: {unique_count}")

        if count != unique_count:
            print("WARNING: Duplicate reactions found, may need cleanup")

        conn.close()
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    fix_post_reactions_schema()