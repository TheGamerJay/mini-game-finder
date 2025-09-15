from flask import Blueprint, jsonify, url_for
from datetime import datetime, timezone
from models import Heartbeat

bp = Blueprint("diag_sched", __name__, url_prefix="/__diag")

@bp.get("/healthz")
def healthz():
    """Basic health check"""
    return jsonify(ok=True, timestamp=datetime.utcnow().isoformat(), app="mini-word-finder")

@bp.get("/scheduler")
def scheduler_status():
    """Show scheduler heartbeats and status"""
    try:
        rows = Heartbeat.query.all()
        heartbeats = {}
        for row in rows:
            # Convert to ISO format with timezone for easy reading
            heartbeats[row.name] = row.last_run.replace(tzinfo=timezone.utc).isoformat()

        return jsonify(
            ok=True,
            heartbeats=heartbeats,
            workers_expected=["decay", "wars"],
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@bp.get("/routes")
def routes_list():
    """List all registered routes for debugging"""
    from flask import current_app

    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods),
            "path": rule.rule
        })

    # Sort by path for easier reading
    routes.sort(key=lambda x: x["path"])

    return jsonify(ok=True, routes=routes, count=len(routes))

@bp.get("/selftest")
def selftest():
    """One-line smoke check to verify all diagnostic endpoints"""
    from flask import current_app
    client = current_app.test_client()
    r1 = client.get("/__diag/healthz").status_code == 200
    r2 = client.get("/__diag/scheduler").status_code == 200
    return ({"ok": r1 and r2}, 200 if (r1 and r2) else 500)