#!/usr/bin/env bash
set -euo pipefail

# --- optional: wait for Postgres if you sometimes race it ---
if [[ -n "${DATABASE_URL:-}" ]]; then
  echo "[start] waiting for database to accept connections..."
  for i in {1..30}; do
    if python - <<'PY' >/dev/null 2>&1
import sys, os, psycopg2
from urllib.parse import urlparse
u=urlparse(os.environ['DATABASE_URL'].replace('postgres://','postgresql://'))
psycopg2.connect(dbname=u.path[1:], user=u.username, password=u.password,
                 host=u.hostname, port=u.port).close()
PY
    then
      echo "[start] db is up."
      break
    fi
    sleep 1
  done
fi

# --- optional: run migrations (no-op if you don't use them) ---
# flask db upgrade || true
# alembic upgrade head || true

# Gunicorn (simple, reliable)
export PORT="${PORT:-8080}"
echo "[start] launching gunicorn on 0.0.0.0:$PORT"
exec gunicorn "wsgi:app" \
  --bind 0.0.0.0:$PORT \
  --workers 2 \
  --threads 4 \
  --timeout 60 \
  --access-logfile - --error-logfile - --log-level info