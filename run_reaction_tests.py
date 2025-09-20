#!/usr/bin/env python3
"""
Simple test runner for reaction functionality.
Run this to verify the reaction system works correctly.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set test environment
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

try:
    import pytest
    print("Running reaction tests...")
    exit_code = pytest.main([
        'test_reactions.py',
        '-v',  # Verbose output
        '--tb=short',  # Short traceback format
        '--no-header',  # No pytest header
    ])

    if exit_code == 0:
        print("\n✅ All reaction tests passed!")
    else:
        print(f"\n❌ Some tests failed (exit code: {exit_code})")

    sys.exit(exit_code)

except ImportError:
    print("❌ pytest not installed. Installing pytest...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pytest'])
    print("✅ pytest installed. Please run this script again.")
    sys.exit(1)

except Exception as e:
    print(f"❌ Error running tests: {e}")
    sys.exit(1)