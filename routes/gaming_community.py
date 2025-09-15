from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Post, PostBoost, User, UserBadge
from services.credits import spend_credits_v2, NotEnoughCredits
from services.war_badges_catalog import level_theme
from datetime import datetime
import json

gaming_community_bp = Blueprint("gaming_community", __name__)

BOOST_COST = 10
BOOST_POINTS = 10

@gaming_community_bp.route("/api/community/boost", methods=["POST"])
@login_required
def boost_post():
    data = request.get_json() or {}
    post_id = data.get("postId")
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"success": False, "error": "Post not found"}), 404

    try:
        remaining = spend_credits_v2(current_user.id, BOOST_COST, "boost", meta={"post_id": post.id})
        post.boost_score = (post.boost_score or 0) + BOOST_POINTS
        post.last_boost_at = datetime.utcnow()
        db.session.add(PostBoost(post_id=post.id, user_id=current_user.id, credits_spent=BOOST_COST))
        db.session.commit()
        return jsonify({
            "success": True,
            "remaining": remaining,
            "post": {"id": post.id, "boost_score": post.boost_score}
        })
    except NotEnoughCredits as e:
        return jsonify({"success": False, "error": str(e)}), 400

@gaming_community_bp.route("/api/community/feed", methods=["GET"])
@login_required
def community_feed():
    posts = (Post.query
             .filter_by(is_hidden=False)
             .order_by(
                 Post.boost_score.desc(),
                 Post.last_boost_at.desc().nullslast(),
                 Post.created_at.desc()
             )
             .limit(100).all())

    def get_author_info(user_id):
        user = User.query.get(user_id)
        if not user:
            return {"id": user_id, "name": "Unknown", "avatar": None, "war_badge": None}

        badge = UserBadge.query.filter_by(user_id=user.id, code="war_champion_lvl").first()
        war_badge = None
        if badge:
            theme = level_theme(badge.level)
            if theme:
                war_badge = {
                    "level": badge.level,
                    "wins": user.war_wins or 0,
                    "name": theme["name"],
                    "icon": theme["icon"],
                    "theme": theme["theme"]
                }

        return {
            "id": user.id,
            "name": user.display_name or user.username,
            "avatar": user.profile_image_data or user.profile_image_url,
            "war_badge": war_badge
        }

    feed_posts = []
    for post in posts:
        feed_posts.append({
            "id": post.id,
            "user_id": post.user_id,
            "body": post.body,
            "image_url": post.image_url,
            "boost_score": post.boost_score or 0,
            "last_boost_at": post.last_boost_at.isoformat() if post.last_boost_at else None,
            "created_at": post.created_at.isoformat(),
            "author": get_author_info(post.user_id)
        })

    return jsonify({"posts": feed_posts})