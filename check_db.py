import os
from sqlalchemy import create_engine, text

# Use Railway's DATABASE_URL (set in environment variables)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found. Did you set it in Railway or PowerShell?")

# Connect
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("✅ Connected to database")

    # Check if users table exists
    try:
        result = conn.execute(text("SELECT * FROM users LIMIT 5"))
        print("\n--- Users Table ---")
        for row in result:
            print(row)
    except Exception as e:
        print("⚠️ Could not query users table:", e)

    # Check if scores table exists
    try:
        result = conn.execute(text("SELECT * FROM scores LIMIT 5"))
        print("\n--- Scores Table ---")
        for row in result:
            print(row)
    except Exception as e:
        print("⚠️ Could not query scores table:", e)