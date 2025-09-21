from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Post, PostBoost, User, UserBadge
from services.credits import spend_credits_v2, NotEnoughCredits
from services.war_badges_catalog import level_theme
from csrf_utils import require_csrf
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

gaming_community_bp = Blueprint("gaming_community", __name__)

BOOST_COST = 10
BOOST_POINTS = 10

def _check_boost_penalty(user_id):
    """Check if user is under boost penalty."""
    user = User.query.get(user_id)
    if user and user.boost_penalty_until:
        if datetime.utcnow() < user.boost_penalty_until:
            remaining = user.boost_penalty_until - datetime.utcnow()
            hours = int(remaining.total_seconds() / 3600)
            return f"You are under boost penalty for {hours} more hours"
    return None

def _check_post_cooldown(post_id):
    """Check if post is under boost cooldown."""
    post = Post.query.get(post_id)
    if post and post.boost_cooldown_until:
        if datetime.utcnow() < post.boost_cooldown_until:
            remaining = post.boost_cooldown_until - datetime.utcnow()
            hours = int(remaining.total_seconds() / 3600)
            return f"This post is under boost cooldown for {hours} more hours"
    return None

@gaming_community_bp.route("/api/community/boost", methods=["POST"])
@login_required
@require_csrf
def boost_post():
    data = request.get_json() or {}
    post_id = data.get("postId")

    if not post_id:
        return jsonify({"success": False, "error": "Post ID is required"}), 400

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"success": False, "error": "Post not found"}), 404

    # Check if user is under boost penalty
    penalty_error = _check_boost_penalty(current_user.id)
    if penalty_error:
        return jsonify({"success": False, "error": penalty_error}), 400

    # Check if post is under boost cooldown
    cooldown_error = _check_post_cooldown(post_id)
    if cooldown_error:
        return jsonify({"success": False, "error": cooldown_error}), 400

    try:
        logger.info(f"User {current_user.id} attempting to boost post {post_id} for {BOOST_COST} credits")

        # Deduct credits first - this will raise NotEnoughCredits if insufficient
        remaining = spend_credits_v2(current_user.id, BOOST_COST, "boost", meta={"post_id": post.id})

        # Apply boost to post
        post.boost_score = (post.boost_score or 0) + BOOST_POINTS
        post.last_boost_at = datetime.utcnow()

        # Record the boost transaction
        db.session.add(PostBoost(post_id=post.id, user_id=current_user.id, credits_spent=BOOST_COST))

        # Commit all changes
        db.session.commit()

        logger.info(f"Post {post_id} boosted successfully by user {current_user.id}. Remaining credits: {remaining}")

        return jsonify({
            "success": True,
            "remaining": remaining,
            "post": {"id": post.id, "boost_score": post.boost_score},
            "message": f"Post boosted! You have {remaining} credits remaining."
        })

    except NotEnoughCredits as e:
        logger.warning(f"User {current_user.id} tried to boost post {post_id} but has insufficient credits: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        # If anything fails after spending credits, the transaction will rollback automatically
        db.session.rollback()
        logger.error(f"Error boosting post {post_id} for user {current_user.id}: {e}")
        return jsonify({"success": False, "error": "Something went wrong. Your credits have been refunded."}), 500

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