#!/usr/bin/env python3
"""
Database Schema Diagnostic Tool
Checks what actually exists in production vs what models expect
"""

import sys
import os
sys.path.append('.')

# Import the Flask app correctly
exec(open('app.py').read())  # This will run app.py and make 'app' available
from sqlalchemy import text, inspect
import logging

def diagnose_schema():
    """Comprehensive schema analysis"""
    with app.app_context():
        inspector = inspect(db.engine)

        print("🔍 DATABASE SCHEMA DIAGNOSTIC")
        print("=" * 50)

        # Get all actual tables
        actual_tables = set(inspector.get_table_names())
        print(f"\n📊 ACTUAL TABLES IN DATABASE ({len(actual_tables)}):")
        for table in sorted(actual_tables):
            print(f"  ✅ {table}")

        # Expected tables from models
        expected_tables = {
            'posts', 'post_reactions', 'post_reports', 'user_community_stats',
            'community_mutes', 'users', 'boost_wars', 'boost_war_actions'
        }

        print(f"\n📋 EXPECTED TABLES FROM MODELS ({len(expected_tables)}):")
        missing_tables = expected_tables - actual_tables
        existing_expected = expected_tables & actual_tables

        for table in sorted(existing_expected):
            print(f"  ✅ {table}")

        for table in sorted(missing_tables):
            print(f"  ❌ MISSING: {table}")

        # Check specific problematic tables
        problematic_checks = {
            'posts': ['is_hidden', 'is_deleted', 'moderation_status', 'boost_cooldown_until'],
            'post_reactions': ['id', 'post_id', 'user_id', 'reaction_type', 'created_at'],
            'user_community_stats': ['total_reactions_given', 'total_reactions_received', 'last_reaction_at'],
            'users': ['challenge_penalty_until', 'boost_penalty_until']
        }

        print(f"\n🔍 DETAILED COLUMN ANALYSIS:")
        print("-" * 30)

        for table, expected_columns in problematic_checks.items():
            if table in actual_tables:
                print(f"\n📄 TABLE: {table}")
                actual_columns = {col['name'] for col in inspector.get_columns(table)}

                print(f"  ✅ EXISTS - Checking columns...")
                for col in expected_columns:
                    if col in actual_columns:
                        print(f"    ✅ {col}")
                    else:
                        print(f"    ❌ MISSING: {col}")

                # Show all actual columns
                print(f"  📊 ALL ACTUAL COLUMNS:")
                for col in sorted(actual_columns):
                    print(f"    • {col}")
            else:
                print(f"\n❌ TABLE MISSING: {table}")
                print(f"  Expected columns: {', '.join(expected_columns)}")

        # Test some specific queries that have been failing
        print(f"\n🧪 TESTING PROBLEMATIC QUERIES:")
        print("-" * 35)

        test_queries = [
            ("Post hidden/deleted check",
             "SELECT COUNT(*) FROM posts WHERE (is_hidden = false OR is_hidden IS NULL) AND (is_deleted = false OR is_deleted IS NULL)"),
            ("Reaction count",
             "SELECT COUNT(*) FROM post_reactions WHERE reaction_type = 'love'"),
            ("User stats check",
             "SELECT COUNT(*) FROM user_community_stats WHERE total_reactions_given > 0"),
            ("Basic post check",
             "SELECT COUNT(*) FROM posts WHERE id IS NOT NULL")
        ]

        for description, query in test_queries:
            try:
                result = db.session.execute(text(query)).scalar()
                print(f"  ✅ {description}: {result} rows")
            except Exception as e:
                print(f"  ❌ {description}: FAILED - {str(e)[:100]}...")

        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 20)

        if missing_tables:
            print(f"  🔧 Missing tables need to be created: {', '.join(missing_tables)}")

        if 'posts' in actual_tables:
            posts_columns = {col['name'] for col in inspector.get_columns('posts')}
            missing_post_cols = {'is_hidden', 'is_deleted', 'moderation_status'} - posts_columns
            if missing_post_cols:
                print(f"  🔧 Posts table missing columns: {', '.join(missing_post_cols)}")

        if 'post_reactions' in actual_tables:
            reactions_columns = {col['name'] for col in inspector.get_columns('post_reactions')}
            if 'reaction_type' not in reactions_columns:
                print(f"  🔧 post_reactions missing reaction_type column")
            if 'id' not in reactions_columns:
                print(f"  🔧 post_reactions missing id primary key")

        print(f"\n✅ DIAGNOSIS COMPLETE")

if __name__ == "__main__":
    try:
        diagnose_schema()
    except Exception as e:
        print(f"❌ Error running diagnosis: {e}")
        import traceback
        traceback.print_exc()