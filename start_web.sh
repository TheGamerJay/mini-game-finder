#!/usr/bin/env bash
set -euo pipefail
: "${PORT:=5000}"

echo "=== RAILWAY STARTUP SCRIPT STARTING ===" >&2
echo "PWD: $(pwd)" >&2
echo "PORT: $PORT" >&2

# Initialize database
echo "=== INITIALIZING DATABASE ===" >&2
python init_db.py

echo "=== STARTING GUNICORN ===" >&2
exec gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 --keep-alive 5