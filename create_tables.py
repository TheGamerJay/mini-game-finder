#!/usr/bin/env python3
"""
Simple script to create all database tables.
Run this after deploying new models to ensure tables exist.
"""

import os
from app import app
from models import db

def create_tables():
    with app.app_context():
        print("Creating all database tables...")
        try:
            db.create_all()
            print("✅ All tables created successfully!")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            raise

if __name__ == "__main__":
    create_tables()