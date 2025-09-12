#!/usr/bin/env python3
"""
Emergency database fix script to add missing columns
"""

import os
from sqlalchemy import create_engine, text

def get_db_url():
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url or "sqlite:///local.db"

def fix_database():
    db_url = get_db_url()
    print(f"Connecting to: {db_url[:50]}...")
    
    engine = create_engine(db_url)
    
    # Create missing columns
    with engine.connect() as conn:
        # Check if users table exists
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'users'
        """))
        
        if not result.fetchone():
            print("Users table doesn't exist. Creating it...")
            conn.execute(text("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE,
                    email VARCHAR(255) UNIQUE,
                    password_hash VARCHAR(255),
                    display_name VARCHAR(80),
                    profile_image_url VARCHAR(512),
                    mini_word_credits INTEGER NOT NULL DEFAULT 0,
                    is_banned BOOLEAN NOT NULL DEFAULT false,
                    is_admin BOOLEAN NOT NULL DEFAULT false,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    weekly_pass_until DATE,
                    display_name_changed_at TIMESTAMPTZ,
                    boosts_day DATE,
                    boosts_used INTEGER NOT NULL DEFAULT 0
                )
            """))
            conn.commit()
            print("Users table created successfully!")
        else:
            print("Users table exists. Adding missing columns...")
            
            # Add missing columns
            missing_columns = [
                ("username", "VARCHAR(50) UNIQUE"),
                ("email", "VARCHAR(255) UNIQUE"),
                ("password_hash", "VARCHAR(255)"),
                ("display_name", "VARCHAR(80)"),
                ("profile_image_url", "VARCHAR(512)"),
                ("mini_word_credits", "INTEGER NOT NULL DEFAULT 0"),
                ("is_banned", "BOOLEAN NOT NULL DEFAULT false"),
                ("is_admin", "BOOLEAN NOT NULL DEFAULT false"),
                ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
                ("updated_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
                ("weekly_pass_until", "DATE"),
                ("display_name_changed_at", "TIMESTAMPTZ"),
                ("boosts_day", "DATE"),
                ("boosts_used", "INTEGER NOT NULL DEFAULT 0")
            ]
            
            for col_name, col_def in missing_columns:
                try:
                    # Check if column exists
                    result = conn.execute(text("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='users' AND column_name=:col_name
                    """), {"col_name": col_name})
                    
                    if not result.fetchone():
                        print(f"Adding column: {col_name}")
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                    else:
                        print(f"Column {col_name} already exists")
                except Exception as e:
                    print(f"Error adding {col_name}: {e}")
            
            # Add updated_at trigger for proper timestamp management
            print("Setting up updated_at trigger...")
            try:
                conn.execute(text("""
                    -- Add updated_at column if missing
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
                    
                    -- Create trigger function for auto-updating updated_at
                    CREATE OR REPLACE FUNCTION set_users_updated_at()
                    RETURNS TRIGGER AS $trigger$
                    BEGIN
                      NEW.updated_at := NOW();
                      RETURN NEW;
                    END;
                    $trigger$ LANGUAGE plpgsql;
                    
                    -- Drop existing trigger if exists
                    DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
                    
                    -- Create trigger
                    CREATE TRIGGER trg_users_updated_at
                    BEFORE UPDATE ON users
                    FOR EACH ROW
                    EXECUTE FUNCTION set_users_updated_at();
                """))
                conn.commit()
                print("Updated_at trigger created successfully!")
            except Exception as e:
                print(f"Error setting up updated_at trigger: {e}")
            
            print("Database fix completed!")

if __name__ == "__main__":
    fix_database()