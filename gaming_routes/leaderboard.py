from flask import Blueprint, jsonify
from models import User

leaderboard_bp = Blueprint("leaderboard", __name__)

@leaderboard_bp.route("/api/leaderboard/war-wins", methods=["GET"])
def war_wins_leaderboard():
    leaders = (User.query
               .filter(User.war_wins > 0)
               .order_by(User.war_wins.desc())
               .limit(50)
               .all())

    leaderboard_data = []
    for user in leaders:
        leaderboard_data.append({
            "user_id": user.id,
            "name": user.display_name or user.username,
            "avatar": user.profile_image_data or user.profile_image_url,
            "wins": user.war_wins or 0
        })

    return jsonify({"leaders": leaderboard_data})