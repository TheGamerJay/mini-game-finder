from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import UserBadge
from services.war_badges_catalog import level_theme, get_catalog

badges_bp = Blueprint("badges", __name__)

@badges_bp.route("/api/me/war-badge", methods=["GET"])
@login_required
def me_war_badge():
    ub = UserBadge.query.filter_by(user_id=current_user.id, code="war_champion_lvl").first()
    if not ub:
        return jsonify({"has_badge": False})

    theme = level_theme(ub.level)
    return jsonify({
        "has_badge": True,
        "level": ub.level,
        "wins": current_user.war_wins or 0,
        "name": theme["name"] if theme else f"War Champion Lv{ub.level}",
        "icon": theme["icon"] if theme else "trophy",
        "theme": theme["theme"] if theme else "gold"
    })

@badges_bp.route("/api/badges/war-catalog", methods=["GET"])
def war_catalog():
    return jsonify({"levels": get_catalog()})