#!/usr/bin/env python3
"""
Simple Schema Check - Identify the root cause of systematic schema mismatches
"""

import psycopg2
import os
from urllib.parse import urlparse

def check_production_schema():
    """Check what actually exists in database"""
    # Check local SQLite database first
    import sqlite3

    print("DATABASE SCHEMA CHECK")
    print("=" * 50)

    try:
        # Try local SQLite first
        conn = sqlite3.connect('instance/local.db')
        cur = conn.cursor()

        print("\nConnected to local SQLite database")

        # Get all tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cur.fetchall()]

        print(f"\nACTUAL TABLES ({len(tables)}):")
        for table in tables:
            print(f"  + {table}")

        # Check specific problematic tables
        critical_tables = ['posts', 'post_reactions', 'users', 'user_community_stats']

        for table in critical_tables:
            if table in tables:
                print(f"\nTABLE: {table}")
                # Get column info for SQLite
                cur.execute(f"PRAGMA table_info({table})")
                columns = cur.fetchall()

                for col_info in columns:
                    col_name = col_info[1]
                    col_type = col_info[2]
                    not_null = "NOT NULL" if col_info[3] else "NULL"
                    print(f"  - {col_name} ({col_type}) {not_null}")
            else:
                print(f"\nMISSING TABLE: {table}")

        conn.close()
        return True

    except Exception as e:
        print(f"Local SQLite failed: {e}")
        return False

    # Parse database URL
    parsed = urlparse(database_url)
    if parsed.scheme.startswith('postgres'):
        # Fix Heroku/Railway postgres:// -> postgresql://
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        print("🔍 PRODUCTION DATABASE SCHEMA CHECK")
        print("=" * 50)

        # Get all tables
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        tables = [row[0] for row in cur.fetchall()]

        print(f"\n📊 ACTUAL TABLES ({len(tables)}):")
        for table in tables:
            print(f"  ✅ {table}")

        # Check specific problematic tables
        critical_tables = ['posts', 'post_reactions', 'users', 'user_community_stats']

        for table in critical_tables:
            if table in tables:
                print(f"\n📄 TABLE: {table}")
                # Get column info
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s AND table_schema = 'public'
                    ORDER BY ordinal_position
                """, (table,))
                columns = cur.fetchall()

                for col_name, data_type, nullable in columns:
                    print(f"  • {col_name} ({data_type}) {'NULL' if nullable == 'YES' else 'NOT NULL'}")
            else:
                print(f"\n❌ MISSING TABLE: {table}")

        # Test specific problematic queries
        print(f"\n🧪 TESTING PROBLEMATIC OPERATIONS:")
        print("-" * 40)

        # Test 1: Check posts table structure
        if 'posts' in tables:
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'posts'")
                post_columns = [row[0] for row in cur.fetchall()]
                critical_post_columns = ['is_hidden', 'is_deleted', 'moderation_status', 'boost_cooldown_until']

                print(f"  📄 POSTS TABLE ANALYSIS:")
                for col in critical_post_columns:
                    if col in post_columns:
                        print(f"    ✅ {col}")
                    else:
                        print(f"    ❌ MISSING: {col}")
            except Exception as e:
                print(f"  ❌ Posts analysis failed: {e}")

        # Test 2: Check post_reactions table structure
        if 'post_reactions' in tables:
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'post_reactions'")
                reaction_columns = [row[0] for row in cur.fetchall()]
                critical_reaction_columns = ['id', 'post_id', 'user_id', 'reaction_type', 'created_at']

                print(f"  📄 POST_REACTIONS TABLE ANALYSIS:")
                for col in critical_reaction_columns:
                    if col in reaction_columns:
                        print(f"    ✅ {col}")
                    else:
                        print(f"    ❌ MISSING: {col}")

                # Check for permanent reactions trigger
                cur.execute("""
                    SELECT tgname FROM pg_trigger
                    WHERE tgrelid = (SELECT oid FROM pg_class WHERE relname = 'post_reactions')
                """)
                triggers = [row[0] for row in cur.fetchall()]
                if triggers:
                    print(f"    🔧 TRIGGERS: {', '.join(triggers)}")

            except Exception as e:
                print(f"  ❌ Reactions analysis failed: {e}")

        # Test 3: Check user_community_stats
        if 'user_community_stats' in tables:
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'user_community_stats'")
                stats_columns = [row[0] for row in cur.fetchall()]
                print(f"  📄 USER_COMMUNITY_STATS COLUMNS: {', '.join(stats_columns)}")
            except Exception as e:
                print(f"  ❌ Stats analysis failed: {e}")
        else:
            print(f"  ❌ USER_COMMUNITY_STATS TABLE MISSING")

        print(f"\n💡 ROOT CAUSE SUMMARY:")
        print("-" * 25)
        print("The systematic pattern suggests:")
        print("• Models were created/updated but migrations never ran")
        print("• Production database has older schema than code expects")
        print("• Need comprehensive migration to align schema with models")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    check_production_schema()