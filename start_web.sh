#!/usr/bin/env bash
set -euo pipefail
: "${PORT:=5000}"
# If you prefer Flask dev server:
# python app.py
# Recommended: gunicorn (prod):
exec gunicorn -w 2 -b 0.0.0.0:"$PORT" wsgi:app