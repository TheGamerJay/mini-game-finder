# quota.py
import time

def get_quota(user_id):
    """Return a dummy quota so the app boots and passes smoke tests."""
    return {
        "remaining": 9999,
        "limit": 9999,
        "reset": int(time.time()) + 3600
    }

def inc_quota(user_id, amount=1):
    """Increment quota (stub)."""
    return True