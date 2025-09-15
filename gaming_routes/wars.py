from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import db, Post, BoostWar, BoostWarAction
from services.credits import spend_credits_v2, NotEnoughCredits

wars_bp = Blueprint("wars", __name__)

WARS_DURATION_MIN = 180
COST_INVITE = 0
COST_WAR_BOOST = 10
COST_WAR_UNBOOST = 20
POINTS_WAR_BOOST = 10
POINTS_WAR_UNBOOST = 10

@wars_bp.route("/api/wars/challenge", methods=["POST"])
@login_required
def wars_challenge():
    data = request.get_json() or {}
    challenged_user_id = data.get("challengedUserId")
    challenger_post_id = data.get("challengerPostId")

    if not challenged_user_id:
        return jsonify({"success": False, "error": "Missing challengedUserId"}), 400

    if COST_INVITE > 0:
        try:
            spend_credits_v2(current_user.id, COST_INVITE, "war_invite", meta={"challenged_user_id": challenged_user_id})
        except NotEnoughCredits as e:
            return jsonify({"success": False, "error": str(e)}), 400

    war = BoostWar(
        challenger_user_id=current_user.id,
        challenger_post_id=challenger_post_id,
        challenged_user_id=int(challenged_user_id),
        status="pending"
    )
    db.session.add(war)
    db.session.commit()

    return jsonify({"success": True, "war": {"id": war.id, "status": war.status}})

@wars_bp.route("/api/wars/accept", methods=["POST"])
@login_required
def wars_accept():
    data = request.get_json() or {}
    war = BoostWar.query.get(data.get("warId"))
    challenged_post_id = data.get("challengedPostId")

    if not war or war.status != "pending":
        return jsonify({"success": False, "error": "Invalid war"}), 400

    if war.challenged_user_id != current_user.id:
        return jsonify({"success": False, "error": "Not your invite"}), 403

    war.challenged_post_id = challenged_post_id
    war.status = "active"
    war.starts_at = datetime.utcnow()
    war.ends_at = war.starts_at + timedelta(minutes=WARS_DURATION_MIN)
    db.session.commit()

    return jsonify({
        "success": True,
        "war": {
            "id": war.id,
            "status": war.status,
            "ends_at": war.ends_at.isoformat()
        }
    })

@wars_bp.route("/api/wars/decline", methods=["POST"])
@login_required
def wars_decline():
    data = request.get_json() or {}
    war = BoostWar.query.get(data.get("warId"))

    if not war or war.status != "pending":
        return jsonify({"success": False, "error": "Invalid war"}), 400

    if war.challenged_user_id != current_user.id:
        return jsonify({"success": False, "error": "Not your invite"}), 403

    war.status = "declined"
    db.session.commit()
    return jsonify({"success": True})

def _guard_war(war, actor_id):
    if not war or war.status != "active":
        return "War not active"

    now = datetime.utcnow()
    if now >= war.ends_at:
        return "War ended"

    if actor_id not in (war.challenger_user_id, war.challenged_user_id):
        return "Not a participant"

    return None

@wars_bp.route("/api/wars/action", methods=["POST"])
@login_required
def wars_action():
    data = request.get_json() or {}
    war = BoostWar.query.get(data.get("warId"))
    action = data.get("action")

    if action not in ("boost", "unboost"):
        return jsonify({"success": False, "error": "Invalid action"}), 400

    error = _guard_war(war, current_user.id)
    if error:
        return jsonify({"success": False, "error": error}), 400

    if current_user.id == war.challenger_user_id:
        my_post_id, opp_post_id = war.challenger_post_id, war.challenged_post_id
    else:
        my_post_id, opp_post_id = war.challenged_post_id, war.challenger_post_id

    target_post_id = my_post_id if action == "boost" else opp_post_id
    cost = COST_WAR_BOOST if action == "boost" else COST_WAR_UNBOOST
    delta = POINTS_WAR_BOOST if action == "boost" else -POINTS_WAR_UNBOOST

    try:
        remaining = spend_credits_v2(current_user.id, cost, f"war_{action}", meta={"war_id": war.id, "target_post_id": target_post_id})
    except NotEnoughCredits as e:
        return jsonify({"success": False, "error": str(e)}), 400

    post = Post.query.get(target_post_id)
    post.boost_score = max((post.boost_score or 0) + delta, 0)

    db.session.add(BoostWarAction(
        war_id=war.id,
        actor_user_id=current_user.id,
        target_post_id=target_post_id,
        action=action,
        credits_spent=cost,
        points_delta=delta
    ))
    db.session.commit()

    return jsonify({
        "success": True,
        "remaining": remaining,
        "post": {"id": post.id, "boost_score": post.boost_score}
    })

@wars_bp.route("/api/wars/status", methods=["GET"])
@login_required
def wars_status():
    war = BoostWar.query.get(request.args.get("warId", type=int))
    if not war:
        return jsonify({"success": False, "error": "Not found"}), 404

    return jsonify({
        "success": True,
        "war": {
            "id": war.id,
            "status": war.status,
            "starts_at": war.starts_at.isoformat() if war.starts_at else None,
            "ends_at": war.ends_at.isoformat() if war.ends_at else None,
            "winner_user_id": war.winner_user_id,
            "challenger_final_score": war.challenger_final_score,
            "challenged_final_score": war.challenged_final_score
        }
    })