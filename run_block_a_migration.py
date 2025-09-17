#!/usr/bin/env python3
"""
Run Block A migration for credits system
This script safely applies the SQL migration with proper error handling
"""

import os
import sys
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

def run_migration():
    """Execute the Block A migration"""
    print("🧱 Starting Block A migration - Credits System")
    print("=" * 60)

    # Read the migration SQL
    migration_file = os.path.join(os.path.dirname(__file__), 'migrations', 'block_a_credits_system.sql')

    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False

    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    print(f"📄 Read migration file: {migration_file}")
    print(f"📝 Migration size: {len(migration_sql)} characters")

    # Connect to database
    try:
        conn = get_db_connection()
        print("✅ Connected to database successfully")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False

    try:
        with conn:
            with conn.cursor() as cur:
                print("🔄 Executing migration...")

                # Check if migration already applied
                try:
                    cur.execute("""
                        SELECT applied_at FROM migration_log
                        WHERE migration_name = 'block_a_credits_system'
                    """)
                    existing = cur.fetchone()
                    if existing:
                        print(f"⚠️  Migration already applied at: {existing[0]}")
                        print("   Re-running migration (this is safe due to IF NOT EXISTS clauses)")
                except psycopg2.Error:
                    # migration_log table doesn't exist yet, continue
                    print("🆕 First time running migrations")

                # Execute the migration
                cur.execute(migration_sql)

                # Verify key tables were created
                cur.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('user_credits', 'credit_usage', 'puzzle_words', 'user_prefs', 'game_sessions', 'word_reveals')
                    ORDER BY table_name
                """)
                tables = cur.fetchall()

                print("✅ Migration executed successfully!")
                print("📊 Created/verified tables:")
                for table in tables:
                    print(f"   ✓ {table[0]}")

                # Check if users got the games_played_free column
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'games_played_free'
                """)
                if cur.fetchone():
                    print("   ✓ users.games_played_free column added")

                # Check sample words were inserted
                cur.execute("SELECT COUNT(*) FROM words WHERE definition IS NOT NULL")
                word_count = cur.fetchone()[0]
                print(f"   ✓ {word_count} words with definitions available")

                # Check credit sync trigger
                cur.execute("""
                    SELECT trigger_name FROM information_schema.triggers
                    WHERE trigger_name = 'trigger_sync_user_credits'
                """)
                if cur.fetchone():
                    print("   ✓ Credit sync trigger installed")

                print("🎉 Block A migration completed successfully!")
                return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()
        print("🔌 Database connection closed")

def verify_migration():
    """Verify the migration worked correctly"""
    print("\n🔍 Verifying migration...")

    try:
        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                # Test the spend_user_credits function
                print("🧪 Testing credit spending function...")

                # This should work without errors (will create user_credits record if needed)
                try:
                    cur.execute("SELECT spend_user_credits(999999, 0, 'test')")
                    print("   ✓ spend_user_credits function works")
                except Exception as e:
                    if "INSUFFICIENT_CREDITS" in str(e):
                        print("   ✓ spend_user_credits function works (insufficient credits is expected)")
                    else:
                        print(f"   ⚠️  spend_user_credits test failed: {e}")

                # Test get_user_credits function
                cur.execute("SELECT get_user_credits(999999)")
                balance = cur.fetchone()[0]
                print(f"   ✓ get_user_credits function works (balance: {balance})")

    except Exception as e:
        print(f"⚠️  Verification failed: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Block A Migration Runner")
    print("This will create the credits system tables and functions")
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "--verify-only":
        verify_migration()
        sys.exit(0)

    # Load environment variables if .env exists
    if os.path.exists('.env'):
        print("📋 Loading .env file...")
        from dotenv import load_dotenv
        load_dotenv()

    success = run_migration()

    if success:
        verify_migration()
        print("\n🚀 Ready to implement Block B - Flask blueprints!")
        sys.exit(0)
    else:
        print("\n💥 Migration failed. Please check the errors above.")
        sys.exit(1)