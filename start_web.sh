#!/usr/bin/env bash
set -euo pipefail
: "${PORT:=5000}"

echo "=== RAILWAY STARTUP SCRIPT STARTING ===" >&2
echo "PWD: $(pwd)" >&2
echo "PORT: $PORT" >&2

# Initialize database
echo "=== INITIALIZING DATABASE ===" >&2
python init_db.py

# Run production migrations
echo "=== RUNNING PRODUCTION MIGRATIONS ===" >&2
python run_production_migration.py || echo "Migration failed but continuing..."

echo "=== STARTING GUNICORN ===" >&2
exec gunicorn wsgi:app -b 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile -