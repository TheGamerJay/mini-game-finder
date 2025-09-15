#!/usr/bin/env python3
import os
import psycopg2
from urllib.parse import urlparse

def add_display_name_updated_at_column():
    """Add display_name_updated_at column to production database"""

    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not found in environment")
        return

    # Parse the database URL
    parsed = urlparse(database_url)

    # Connect to PostgreSQL
    try:
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password,
            sslmode='require'
        )

        cursor = conn.cursor()

        # Check if display_name_updated_at column exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'display_name_updated_at'
        """)

        if not cursor.fetchone():
            print("Adding display_name_updated_at column...")
            cursor.execute("ALTER TABLE users ADD COLUMN display_name_updated_at TIMESTAMP")
            print("display_name_updated_at column added successfully!")
        else:
            print("display_name_updated_at column already exists")

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
    add_display_name_updated_at_column()