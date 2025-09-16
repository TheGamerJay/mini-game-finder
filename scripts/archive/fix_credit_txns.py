#!/usr/bin/env python3
"""
Quick fix to add missing amount_delta column to credit_txns table
"""
from app import app
from models import db
from sqlalchemy import text

def fix_credit_txns():
    """Add missing amount_delta column"""

    with app.app_context():
        try:
            # Add the missing column
            print("Adding amount_delta column to credit_txns...")
            try:
                db.session.execute(text('ALTER TABLE credit_txns ADD COLUMN amount_delta INTEGER DEFAULT 0 NOT NULL'))
                db.session.commit()
                print("SUCCESS: Added amount_delta column")
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print("INFO: amount_delta column already exists")
                    db.session.rollback()
                else:
                    raise e

            print("SUCCESS: Database fix completed successfully!")

        except Exception as e:
            print(f"ERROR: Fix failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    fix_credit_txns()