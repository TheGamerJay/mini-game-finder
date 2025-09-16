#!/usr/bin/env python3

import os
import psycopg2
from urllib.parse import urlparse

def add_profile_columns():
    """Add missing profile image columns to production database"""

    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not found in environment")
        return

    # Parse the database URL
    parsed = urlparse(database_url)

    # Connect to database
    try:
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:]  # Remove leading '/'
        )

        cursor = conn.cursor()

        # Check if profile_image_url column exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'profile_image_url'
        """)

        if not cursor.fetchone():
            print("Adding profile_image_url column...")
            cursor.execute("ALTER TABLE users ADD COLUMN profile_image_url TEXT")
        else:
            print("profile_image_url column already exists")

        # Check if profile_image_updated_at column exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'profile_image_updated_at'
        """)

        if not cursor.fetchone():
            print("Adding profile_image_updated_at column...")
            cursor.execute("ALTER TABLE users ADD COLUMN profile_image_updated_at TIMESTAMP")
        else:
            print("profile_image_updated_at column already exists")

        # Commit changes
        conn.commit()
        print("Database migration completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_profile_columns()