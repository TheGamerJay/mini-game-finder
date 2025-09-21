#!/usr/bin/env bash
set -euo pipefail
: "${PORT:=5000}"

echo "Railway startup script starting..."
echo "Environment: PORT=$PORT, DATABASE_URL=${DATABASE_URL:0:20}..."

# Initialize database tables before starting web server
echo "Initializing database..."
if python init_db.py; then
    echo "Database initialization successful"
else
    echo "Database initialization failed, continuing anyway..."
fi

# Test wsgi import before starting gunicorn
echo "Testing WSGI import..."
if python -c "import wsgi; print('WSGI import test successful')"; then
    echo "WSGI import test passed"
else
    echo "WSGI import test failed!"
    exit 1
fi

# Start web server
echo "Starting gunicorn web server on port $PORT..."
exec gunicorn --timeout 60 --bind 0.0.0.0:"$PORT" --log-level info wsgi:app