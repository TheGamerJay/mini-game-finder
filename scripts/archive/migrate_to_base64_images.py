#!/usr/bin/env python3
"""
Migration script to add base64 image storage columns to users table
"""
from app import app
from models import db
from sqlalchemy import text

def migrate_database():
    """Add new columns for base64 image storage"""

    with app.app_context():
        try:
            # Check if we're using SQLite or PostgreSQL
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            is_sqlite = 'sqlite' in db_url.lower()

            print(f"Database type detected: {'SQLite' if is_sqlite else 'PostgreSQL'}")

            # Add the new columns
            print("Adding profile_image_data column...")
            try:
                db.session.execute(text('ALTER TABLE users ADD COLUMN profile_image_data TEXT'))
                db.session.commit()
                print("SUCCESS: Added profile_image_data column")
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print("INFO: profile_image_data column already exists")
                    db.session.rollback()
                else:
                    raise e

            print("Adding profile_image_mime_type column...")
            try:
                db.session.execute(text('ALTER TABLE users ADD COLUMN profile_image_mime_type VARCHAR(50)'))
                db.session.commit()
                print("SUCCESS: Added profile_image_mime_type column")
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print("INFO: profile_image_mime_type column already exists")
                    db.session.rollback()
                else:
                    raise e

            print("SUCCESS: Database migration completed successfully!")
            print("\nNew columns added:")
            print("- profile_image_data (TEXT) - stores base64 encoded image data")
            print("- profile_image_mime_type (VARCHAR) - stores MIME type (image/jpeg, video/mp4, etc.)")
            print("\nNote: profile_image_url is kept for backward compatibility")

        except Exception as e:
            print(f"ERROR: Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate_database()