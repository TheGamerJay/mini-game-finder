#!/usr/bin/env python3
"""
Migration: Add gaming platform columns to production database
Adds missing columns for war_wins and boost system to existing tables
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect

def get_database_url():
    """Get database URL from environment"""
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Handle Heroku postgres:// URLs
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_gaming_columns(engine):
    """Add gaming platform columns to existing tables"""

    migrations = []

    # Check and add users.war_wins column
    if not check_column_exists(engine, 'users', 'war_wins'):
        migrations.append({
            'description': 'Add war_wins column to users table',
            'sql': 'ALTER TABLE users ADD COLUMN war_wins INTEGER NOT NULL DEFAULT 0'
        })

    # Check and add posts boost columns
    if not check_column_exists(engine, 'posts', 'boost_score'):
        migrations.append({
            'description': 'Add boost_score column to posts table',
            'sql': 'ALTER TABLE posts ADD COLUMN boost_score INTEGER NOT NULL DEFAULT 0'
        })

    if not check_column_exists(engine, 'posts', 'last_boost_at'):
        migrations.append({
            'description': 'Add last_boost_at column to posts table',
            'sql': 'ALTER TABLE posts ADD COLUMN last_boost_at TIMESTAMP'
        })

    # Run migrations
    if not migrations:
        print("✅ All gaming platform columns already exist")
        return

    print(f"Running {len(migrations)} migrations...")

    with engine.begin() as conn:
        for migration in migrations:
            print(f"  • {migration['description']}")
            conn.execute(text(migration['sql']))

    print("✅ Gaming platform columns added successfully")

def main():
    """Main migration function"""
    print("🚀 Starting gaming platform column migration...")

    database_url = get_database_url()
    print(f"Database: {database_url.split('@')[1] if '@' in database_url else 'Local'}")

    engine = create_engine(database_url)

    try:
        add_gaming_columns(engine)
        print("🎉 Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()