#!/usr/bin/env bash
set -euo pipefail
exec python -m celery -A celery_app.celery worker --loglevel=info --pool=solo