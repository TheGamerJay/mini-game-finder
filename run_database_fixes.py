#!/usr/bin/env python3
"""
Migration script to fix database issues:
1. Missing id column in post_reactions table
2. Null email values in users table
Run this script to apply all necessary fixes.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def _normalize_db_url(url: str | None) -> str | None:
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

def run_migration(conn, migration_name, migration_file):
    """Run a single migration file"""
    print(f"Running migration: {migration_name}")

    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    try:
        # Execute the migration
        result = conn.execute(text(migration_sql))
        print(f"✅ {migration_name} completed successfully!")
        return True
    except Exception as e:
        print(f"❌ {migration_name} failed: {e}")
        return False

def main():
    # Load environment variables
    load_dotenv()

    # Get database URL
    database_url = _normalize_db_url(os.getenv("DATABASE_URL"))
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    print(f"Connecting to database...")

    try:
        # Create engine
        engine = create_engine(database_url)

        # Migrations to run
        migrations = [
            ("Fix post_reactions id column", os.path.join(os.path.dirname(__file__), 'migrations', 'fix_post_reactions_id_column.sql')),
            ("Fix users email nulls", os.path.join(os.path.dirname(__file__), 'migrations', 'fix_users_email_nulls.sql'))
        ]

        # Execute migrations
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            try:
                success_count = 0
                for migration_name, migration_file in migrations:
                    if run_migration(conn, migration_name, migration_file):
                        success_count += 1
                    else:
                        trans.rollback()
                        print(f"❌ Migration failed, rolling back all changes")
                        sys.exit(1)

                trans.commit()
                print(f"✅ All {success_count} migrations completed successfully!")

            except Exception as e:
                trans.rollback()
                print(f"❌ Migration failed: {e}")
                sys.exit(1)

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()