#!/usr/bin/env python3
"""
Add welcome_pack_purchased column to users table
"""

import os
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    """Get database connection from DATABASE_URL"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Parse the URL
    url = urlparse(database_url)

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.path[1:]  # Remove leading slash
    )
    return conn

def add_welcome_pack_column():
    """Add welcome_pack_purchased column to users table"""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # Check if column already exists
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'users'
                    AND column_name = 'welcome_pack_purchased'
                """)

                if cur.fetchone():
                    print("Column 'welcome_pack_purchased' already exists")
                    return

                # Add the column
                print("Adding welcome_pack_purchased column to users table...")
                cur.execute("""
                    ALTER TABLE users
                    ADD COLUMN welcome_pack_purchased BOOLEAN NOT NULL DEFAULT false
                """)

                print("✅ Successfully added welcome_pack_purchased column")

    except Exception as e:
        print(f"❌ Error adding column: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_welcome_pack_column()