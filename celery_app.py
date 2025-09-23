# celery_app.py
import os
from celery import Celery
from datetime import timedelta

# Redis URL: we'll read from CELERY_BROKER_URL/RESULT_BACKEND,
# falling back to REDIS_URL (Railway Redis variable)
REDIS_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"

celery = Celery(
    "mini_game_finder",
    broker=os.getenv("CELERY_BROKER_URL", REDIS_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", REDIS_URL),
    include=["tasks.promotion_wars"]  # register our tasks module
)

# Sensible Celery config
celery.conf.update(
    task_acks_late=True,
    worker_max_tasks_per_child=100,
    broker_transport_options={"visibility_timeout": 3600},  # 1h
)

# Beat schedule (the "bee")
celery.conf.beat_schedule = {
    "finalize-wars-every-30s": {
        "task": "tasks.promotion_wars.finalize_due_wars",
        "schedule": 30.0,
    },
    "notify-expiring-effects-15m": {
        "task": "tasks.promotion_wars.notify_expiring_effects",
        "schedule": 15 * 60.0,
    },
}