"""
Redis-based leaderboard API endpoints
Implements SoulBridge AI scalable leaderboard system
"""
import time
from flask import Blueprint, request, jsonify
from services.leaderboard import leaderboard_service
from csrf_utils import csrf_exempt
from utils.public import public

redis_leaderboard_bp = Blueprint("redis_leaderboard", __name__)

@redis_leaderboard_bp.route("/api/leaderboard/submit", methods=["POST"])
@csrf_exempt
def submit_score():
    """
    Submit a score to the leaderboard
    Body: { user_id, display_name, game_code, score, ts?, sig? }
    """
    data = request.get_json(force=True, silent=True) or {}

    # Required fields
    for field in ["user_id", "display_name", "game_code", "score"]:
        if field not in data:
            return jsonify({"ok": False, "error": f"missing_field:{field}"}), 400

    # Extract data
    user_id = data["user_id"]
    display_name = data["display_name"]
    game_code = data["game_code"]
    score = data["score"]
    ts = data.get("ts")
    sig = data.get("sig")

    # Submit to leaderboard service
    result = leaderboard_service.submit_score(
        user_id=user_id,
        display_name=display_name,
        game_code=game_code,
        score=score,
        ts=ts,
        sig=sig
    )

    if not result["ok"]:
        status_code = 403 if result.get("error") == "bad_signature" else 400
        return jsonify(result), status_code

    return jsonify(result)

@redis_leaderboard_bp.route("/api/leaderboard/top", methods=["GET"])
@public
def top_scores():
    """
    Get top N scores
    Query: game_code (required), n=10, season_id (optional)
    """
    game_code = request.args.get("game_code", "").strip()
    if not game_code:
        return jsonify({"ok": False, "error": "missing_game_code"}), 400

    n = int(request.args.get("n", 10))
    season_id = request.args.get("season_id")

    result = leaderboard_service.get_top_scores(
        game_code=game_code,
        n=n,
        season_id=season_id
    )

    return jsonify(result)

@redis_leaderboard_bp.route("/api/leaderboard/around", methods=["GET"])
@public
def around_me():
    """
    Get scores around a user
    Query: game_code, user_id, window=3, season_id (optional)
    """
    game_code = request.args.get("game_code", "").strip()
    user_id = request.args.get("user_id", "").strip()

    if not game_code or not user_id:
        return jsonify({"ok": False, "error": "missing_params"}), 400

    window = int(request.args.get("window", 3))
    season_id = request.args.get("season_id")

    result = leaderboard_service.get_around_user(
        game_code=game_code,
        user_id=user_id,
        window=window,
        season_id=season_id
    )

    return jsonify(result)

@redis_leaderboard_bp.route("/api/leaderboard/rank", methods=["GET"])
@public
def rank_of_user():
    """
    Get rank for a specific user
    Query: game_code, user_id, season_id (optional)
    """
    game_code = request.args.get("game_code", "").strip()
    user_id = request.args.get("user_id", "").strip()

    if not game_code or not user_id:
        return jsonify({"ok": False, "error": "missing_params"}), 400

    season_id = request.args.get("season_id")

    result = leaderboard_service.get_user_rank(
        game_code=game_code,
        user_id=user_id,
        season_id=season_id
    )

    return jsonify(result)

@redis_leaderboard_bp.route("/api/leaderboard/user_best", methods=["GET"])
@public
def user_best_all_time():
    """
    Get user's all-time best score
    Query: game_code, user_id
    """
    game_code = request.args.get("game_code", "").strip()
    user_id = request.args.get("user_id", "").strip()

    if not game_code or not user_id:
        return jsonify({"ok": False, "error": "missing_params"}), 400

    result = leaderboard_service.get_user_best(
        game_code=game_code,
        user_id=user_id
    )

    return jsonify(result)

@redis_leaderboard_bp.route("/api/leaderboard/sign", methods=["POST"])
def sign_score():
    """
    Server-side score signing endpoint
    Body: { user_id, game_code, score }
    Returns: { signature, timestamp }
    """
    data = request.get_json(force=True, silent=True) or {}

    for field in ["user_id", "game_code", "score"]:
        if field not in data:
            return jsonify({"ok": False, "error": f"missing_field:{field}"}), 400

    user_id = str(data["user_id"])
    game_code = str(data["game_code"])
    score = int(data["score"])
    ts = int(request.args.get("ts") or time.time())

    signature = leaderboard_service.generate_signature(user_id, game_code, score, ts)

    return jsonify({
        "ok": True,
        "signature": signature,
        "timestamp": ts
    })

# Redis leaderboard widget page
@redis_leaderboard_bp.route("/redis-leaderboard", methods=["GET"])
@public
def leaderboard_widget():
    """Serve the Redis leaderboard widget"""
    from flask import render_template
    return render_template('redis_leaderboard.html')

# Health check for Redis leaderboard service
@redis_leaderboard_bp.route("/api/leaderboard/health", methods=["GET"])
@public
def health_check():
    """Health check for leaderboard service"""
    try:
        if leaderboard_service.redis_available:
            # Test Redis connection
            leaderboard_service.redis.ping()
            return jsonify({"ok": True, "service": "redis_leaderboard", "status": "healthy"})
        else:
            return jsonify({"ok": True, "service": "redis_leaderboard", "status": "fallback", "message": "Redis unavailable, using fallback mode"})
    except Exception as e:
        return jsonify({"ok": False, "service": "redis_leaderboard", "status": "unhealthy", "error": str(e)}), 500