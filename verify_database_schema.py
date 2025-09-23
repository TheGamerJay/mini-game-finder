#!/usr/bin/env python3
"""
Database Schema Verification Script
Checks if all required columns exist with correct types
"""

import os
import sys
from sqlalchemy import create_engine, text
from urllib.parse import urlparse

def verify_database_schema():
    """Verify all required columns exist in the database"""

    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL environment variable not set")
        return False

    # Normalize postgres:// to postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    try:
        engine = create_engine(db_url)

        print("🔍 VERIFYING DATABASE SCHEMA")
        print("=" * 50)

        # Required columns with their expected types
        required_columns = {
            'user_community_stats': [
                ('user_id', 'integer'),
                ('posts_today', 'integer'),
                ('reactions_today', 'integer'),
                ('reports_today', 'integer'),
                ('last_post_at', 'timestamp'),
                ('last_reaction_at', 'timestamp'),
                ('last_report_at', 'timestamp'),
                ('last_reset_date', 'date'),
                ('total_posts', 'integer'),
                ('total_reactions_given', 'integer'),
                ('total_reactions_received', 'integer'),
                ('created_at', 'timestamp'),
                ('updated_at', 'timestamp'),
                # Progressive cooldown columns
                ('recent_actions_hour', 'integer'),
                ('recent_actions_reset_at', 'timestamp'),
            ],
            'posts': [
                ('id', 'integer'),
                ('user_id', 'integer'),
                ('body', 'text'),
                ('category', 'character varying'),
                ('content_type', 'character varying'),
                ('created_at', 'timestamp'),
                ('updated_at', 'timestamp'),
            ],
            'post_reactions': [
                ('id', 'integer'),
                ('post_id', 'integer'),
                ('user_id', 'integer'),
                ('reaction_type', 'character varying'),
                ('created_at', 'timestamp'),
            ]
        }

        all_passed = True

        with engine.connect() as conn:
            for table_name, columns in required_columns.items():
                print(f"\n📋 Checking table: {table_name}")
                print("-" * 30)

                # Get all columns for this table
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    ORDER BY ordinal_position
                """), {"table_name": table_name})

                existing_columns = {row[0]: row[1] for row in result}

                if not existing_columns:
                    print(f"❌ Table {table_name} does not exist!")
                    all_passed = False
                    continue

                # Check each required column
                for col_name, expected_type in columns:
                    if col_name in existing_columns:
                        actual_type = existing_columns[col_name]
                        # Normalize type names for comparison
                        if ('timestamp' in expected_type and 'timestamp' in actual_type) or \
                           ('integer' in expected_type and 'integer' in actual_type) or \
                           ('character' in expected_type and 'character' in actual_type) or \
                           (expected_type == actual_type):
                            print(f"✅ {col_name}: {actual_type}")
                        else:
                            print(f"⚠️  {col_name}: expected {expected_type}, got {actual_type}")
                    else:
                        print(f"❌ {col_name}: MISSING")
                        all_passed = False

                # Show any extra columns
                extra_columns = set(existing_columns.keys()) - {col[0] for col in columns}
                if extra_columns:
                    print(f"ℹ️  Extra columns: {', '.join(extra_columns)}")

        print("\n" + "=" * 50)
        if all_passed:
            print("✅ ALL SCHEMA CHECKS PASSED")
            print("🚀 Progressive cooldown system should work correctly")
        else:
            print("❌ SCHEMA ISSUES FOUND")
            print("🔧 Some columns are missing or have incorrect types")

        return all_passed

    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return False

def check_specific_progressive_columns():
    """Quick check for just the progressive cooldown columns"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    try:
        engine = create_engine(db_url)

        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'user_community_stats'
                  AND column_name IN ('recent_actions_hour', 'recent_actions_reset_at')
                ORDER BY column_name
            """))

            columns = list(result)

            print("🎯 PROGRESSIVE COOLDOWN COLUMNS CHECK")
            print("=" * 40)

            if len(columns) == 2:
                for col in columns:
                    print(f"✅ {col[0]}: {col[1]} (nullable: {col[2]})")
                print("\n🚀 Progressive cooldown columns are present!")
            else:
                print(f"❌ Expected 2 columns, found {len(columns)}")
                if columns:
                    for col in columns:
                        print(f"Found: {col[0]}: {col[1]}")
                else:
                    print("No progressive cooldown columns found")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        check_specific_progressive_columns()
    else:
        verify_database_schema()