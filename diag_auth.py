from flask import Blueprint, jsonify
from flask_login import current_user

bp = Blueprint("diag_auth", __name__, url_prefix="/__diag")

@bp.get("/whoami")
def whoami():
    if current_user.is_authenticated:
        return jsonify(ok=True, id=current_user.id)
    return jsonify(ok=False), 401