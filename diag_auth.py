from flask import Blueprint, jsonify
from flask_login import current_user

bp = Blueprint("diag_auth", __name__, url_prefix="/__diag")

@bp.get("/whoami")
def whoami():
    if not current_user.is_authenticated:
        # 200 on purpose to avoid noisy 401 in console
        return jsonify({"ok": True, "authenticated": False}), 200
    return jsonify({
        "ok": True,
        "authenticated": True,
        "user_id": current_user.get_id(),
        "email": getattr(current_user, "email", None),
    }), 200