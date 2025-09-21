from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Post, PostBoost, User, UserBadge
from services.credits import spend_credits_v2, NotEnoughCredits
from services.war_badges_catalog import level_theme
from csrf_utils import require_csrf
from promotion_war_service import PromotionWarService
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

gaming_community_bp = Blueprint("gaming_community", __name__)

BASE_PROMOTION_COST = 10
BASE_PROMOTION_POINTS = 10

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

    # Check if user is under promotion cooldown (from war penalties)
    if PromotionWarService._has_active_debuff(current_user.id, 'PROMOTION_COOLDOWN'):
        return jsonify({"success": False, "error": "You are under promotion cooldown from losing a recent war"}), 400

    # Check if user is under boost penalty (legacy system)
    penalty_error = _check_boost_penalty(current_user.id)
    if penalty_error:
        return jsonify({"success": False, "error": penalty_error}), 400

    # Check if post is under boost cooldown
    cooldown_error = _check_post_cooldown(post_id)
    if cooldown_error:
        return jsonify({"success": False, "error": cooldown_error}), 400

    try:
        # Calculate dynamic cost based on user's war status
        promotion_cost = PromotionWarService.get_promotion_cost(current_user.id, BASE_PROMOTION_COST)
        promotion_points = PromotionWarService.get_promotion_effectiveness(current_user.id, BASE_PROMOTION_POINTS)

        logger.info(f"User {current_user.id} attempting to promote post {post_id} for {promotion_cost} credits (earning {promotion_points} points)")

        # Deduct credits first - this will raise NotEnoughCredits if insufficient
        remaining = spend_credits_v2(current_user.id, promotion_cost, "promotion", meta={"post_id": post.id})

        # Apply promotion to post
        post.boost_score = (post.boost_score or 0) + promotion_points
        post.last_boost_at = datetime.utcnow()

        # Record the promotion transaction
        db.session.add(PostBoost(post_id=post.id, user_id=current_user.id, credits_spent=promotion_cost))

        # Record promotion in any active war
        PromotionWarService.record_promotion_during_war(current_user.id, post_id, promotion_points, promotion_cost)

        # Use discount if applicable
        if promotion_cost < BASE_PROMOTION_COST:
            PromotionWarService.use_discount(current_user.id, 'PROMOTION_DISCOUNT')

        # Commit all changes
        db.session.commit()

        logger.info(f"Post {post_id} promoted successfully by user {current_user.id}. Cost: {promotion_cost}, Points: {promotion_points}, Remaining credits: {remaining}")

        cost_message = ""
        if promotion_cost < BASE_PROMOTION_COST:
            cost_message = f" (discount applied: {promotion_cost} credits instead of {BASE_PROMOTION_COST})"
        elif promotion_cost > BASE_PROMOTION_COST:
            cost_message = f" (penalty applied: {promotion_cost} credits instead of {BASE_PROMOTION_COST})"

        return jsonify({
            "success": True,
            "remaining": remaining,
            "post": {"id": post.id, "boost_score": post.boost_score},
            "message": f"Post promoted{cost_message}! You have {remaining} credits remaining."
        })

    except NotEnoughCredits as e:
        logger.warning(f"User {current_user.id} tried to promote post {post_id} but has insufficient credits: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        # If anything fails after spending credits, the transaction will rollback automatically
        db.session.rollback()
        logger.error(f"Error promoting post {post_id} for user {current_user.id}: {e}")
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