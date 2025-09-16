#!/usr/bin/env python3
"""
Script to reset cooldown timers for testing
Run this to clear both profile_image_updated_at and display_name_updated_at
"""
from app import app
from models import db, User
from sqlalchemy import text

def reset_cooldown_timers():
    """Reset both cooldown timers by setting timestamps to NULL"""

    with app.app_context():
        try:
            # Reset both cooldown timestamps to NULL
            db.session.execute(text("""
                UPDATE users
                SET profile_image_updated_at = NULL,
                    display_name_updated_at = NULL
            """))

            db.session.commit()
            print("✅ Both cooldown timers reset successfully!")
            print("📷 Image upload cooldown: CLEARED")
            print("✏️  Display name cooldown: CLEARED")
            print("\nYou can now test both actions immediately!")

        except Exception as e:
            print(f"❌ Error resetting cooldowns: {e}")
            db.session.rollback()

if __name__ == "__main__":
    reset_cooldown_timers()