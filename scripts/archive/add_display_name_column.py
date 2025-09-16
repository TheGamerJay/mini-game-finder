#!/usr/bin/env python3
"""
Migration script to add display_name_updated_at column
Run this in production: python add_display_name_column.py
"""
import os
from app import app
from models import db
from sqlalchemy import text

def add_display_name_updated_at_column():
    """Add display_name_updated_at column using Flask app context"""

    with app.app_context():
        try:
            # Check if column exists
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'display_name_updated_at'
            """)).fetchone()

            if not result:
                print("Adding display_name_updated_at column...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN display_name_updated_at TIMESTAMP"))
                db.session.commit()
                print("display_name_updated_at column added successfully!")
            else:
                print("display_name_updated_at column already exists")

        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()
            # If the error is about the column not existing, that's expected
            if "column" in str(e).lower() and "does not exist" in str(e).lower():
                print("Column doesn't exist yet, this is expected during migration")
            else:
                raise

if __name__ == "__main__":
    add_display_name_updated_at_column()