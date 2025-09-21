#!/usr/bin/env bash
set -euo pipefail
: "${PORT:=5000}"

echo "=== RAILWAY STARTUP SCRIPT STARTING ===" >&2
echo "PWD: $(pwd)" >&2
echo "Files: $(ls -la)" >&2
echo "PORT: $PORT" >&2
echo "Python version: $(python --version)" >&2

# Skip database init for now to isolate the issue
echo "=== TESTING WSGI IMPORT ===" >&2
python -c "
import sys
print('Python path:', sys.path, file=sys.stderr)
try:
    import wsgi
    print('WSGI import successful!', file=sys.stderr)
    print('App type:', type(wsgi.app), file=sys.stderr)
except Exception as e:
    print('WSGI import failed:', e, file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"

echo "=== STARTING GUNICORN ===" >&2
exec gunicorn --bind 0.0.0.0:"$PORT" --log-level debug --access-logfile - --error-logfile - wsgi:app