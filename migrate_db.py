#!/usr/bin/env python3
"""
Database migration script to add the new columns and tables from the enhanced codebase.
Run this script after updating your models to apply the database changes.

Usage: python migrate_db.py
"""

import os
from app import app, db
from models import User, Score, CreditTxn, Purchase, PuzzleBank, Words, Categories, WordCategories, PuzzlePlays
from sqlalchemy import text

def migrate_database():
    """Apply database migrations for the enhanced Mini Word Finder features"""
    print("Starting database migration...")

    with app.app_context():
        try:
            # Check if we're using SQLite or PostgreSQL
            engine = db.engine
            dialect_name = engine.dialect.name

            print(f"Database dialect: {dialect_name}")

            if dialect_name == 'sqlite':
                # SQLite migrations
                print("Applying SQLite migrations...")

                # Add new columns to users table
                try:
                    db.session.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(80)"))
                    print("Added display_name to users")
                except Exception as e:
                    print(f"WARNING: display_name already exists or error: {e}")

                try:
                    db.session.execute(text("ALTER TABLE users ADD COLUMN profile_image_url TEXT"))
                    print("Added profile_image_url to users")
                except Exception as e:
                    print(f"WARNING: profile_image_url already exists or error: {e}")

                try:
                    db.session.execute(text("ALTER TABLE users ADD COLUMN profile_image_updated_at DATETIME"))
                    print("Added profile_image_updated_at to users")
                except Exception as e:
                    print(f"WARNING: profile_image_updated_at already exists or error: {e}")

                # Add new columns to scores table
                new_score_columns = [
                    ("mode", "VARCHAR(16)"),
                    ("is_daily", "BOOLEAN DEFAULT 0"),
                    ("total_words", "INTEGER DEFAULT 0"),
                    ("found_count", "INTEGER DEFAULT 0"),
                    ("duration_sec", "INTEGER"),
                    ("completed", "BOOLEAN DEFAULT 0"),
                    ("seed", "BIGINT"),
                    ("category", "VARCHAR(64)"),
                    ("hints_used", "INTEGER DEFAULT 0"),
                    ("puzzle_id", "INTEGER")
                ]

                for col_name, col_type in new_score_columns:
                    try:
                        db.session.execute(text(f"ALTER TABLE scores ADD COLUMN {col_name} {col_type}"))
                        print(f"Added {col_name} to scores")
                    except Exception as e:
                        print(f"WARNING: {col_name} already exists or error: {e}")

            elif dialect_name == 'postgresql':
                # PostgreSQL migrations
                print("Applying PostgreSQL migrations...")

                # Users table additions
                pg_user_migrations = [
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(80)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image_url TEXT",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image_updated_at TIMESTAMPTZ"
                ]

                for sql in pg_user_migrations:
                    try:
                        db.session.execute(text(sql))
                        print(f"Executed: {sql}")
                    except Exception as e:
                        print(f"WARNING: Error with {sql}: {e}")

                # Scores table additions
                pg_score_migrations = [
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS mode TEXT",
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS is_daily BOOLEAN NOT NULL DEFAULT FALSE",
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS total_words INTEGER NOT NULL DEFAULT 0",
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS found_count INTEGER NOT NULL DEFAULT 0",
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS duration_sec INTEGER",
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS completed BOOLEAN NOT NULL DEFAULT FALSE",
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS seed BIGINT",
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS category TEXT",
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS hints_used INTEGER NOT NULL DEFAULT 0",
                    "ALTER TABLE scores ADD COLUMN IF NOT EXISTS puzzle_id INT"
                ]

                for sql in pg_score_migrations:
                    try:
                        db.session.execute(text(sql))
                        print(f"Executed: {sql}")
                    except Exception as e:
                        print(f"WARNING: Error with {sql}: {e}")

            # Create all new tables (this will only create tables that don't exist)
            print("Creating new tables...")
            db.create_all()

            # Commit all changes
            db.session.commit()
            print("Database migration completed successfully!")

        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate_database()