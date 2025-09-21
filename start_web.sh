#!/usr/bin/env bash
set -euo pipefail
: "${PORT:=5000}"

# Initialize database tables before starting web server
echo "Initializing database..."
python init_db.py

# Start web server
echo "Starting web server on port $PORT..."
exec gunicorn -w 2 -b 0.0.0.0:"$PORT" wsgi:app