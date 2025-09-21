from flask import Blueprint, jsonify
from models import User, Score
from sqlalchemy import func, desc

leaderboard_bp = Blueprint("leaderboard", __name__)

@leaderboard_bp.route("/api/leaderboard/word-finder", methods=["GET"])
def word_finder_leaderboard():
    """Get Word Finder leaderboard showing top players by completion rate and speed"""
    try:
        # Get top players based on completed games, completion rate, and average time
        leaders_query = (
            Score.query
            .join(User, Score.user_id == User.id)
            .filter(Score.completed == True)
            .filter(Score.game_mode == 'mini_word_finder')
            .with_entities(
                User.id,
                User.display_name,
                User.username,
                User.profile_image_data,
                User.profile_image_url,
                func.count(Score.id).label('completed_games'),
                func.avg(Score.duration_sec).label('avg_time'),
                func.avg(Score.found_count * 100.0 / func.nullif(func.coalesce(Score.total_words, func.greatest(Score.found_count, 1)), 0)).label('avg_completion_rate'),
                func.max(Score.created_at).label('last_played')
            )
            .group_by(User.id, User.display_name, User.username, User.profile_image_data, User.profile_image_url)
            .having(func.count(Score.id) >= 3)  # Must have at least 3 completed games
            .order_by(desc('completed_games'), 'avg_time')
            .limit(50)
            .all()
        )

        leaderboard_data = []
        for leader in leaders_query:
            avg_minutes = int(leader.avg_time // 60) if leader.avg_time else 0
            avg_seconds = int(leader.avg_time % 60) if leader.avg_time else 0

            leaderboard_data.append({
                "user_id": leader.id,
                "name": leader.display_name or leader.username,
                "avatar": leader.profile_image_data or leader.profile_image_url,
                "completed_games": leader.completed_games,
                "avg_time": f"{avg_minutes}:{avg_seconds:02d}",
                "avg_completion_rate": round(leader.avg_completion_rate or 0, 1),
                "last_played": leader.last_played.strftime('%Y-%m-%d') if leader.last_played else None
            })

        return jsonify({"leaders": leaderboard_data, "total": len(leaderboard_data)})

    except Exception as e:
        return jsonify({"error": str(e), "leaders": []}), 500

@leaderboard_bp.route("/api/leaderboard/word-finder/<mode>", methods=["GET"])
def word_finder_mode_leaderboard(mode):
    """Get Word Finder leaderboard for specific difficulty mode (easy/medium/hard)"""
    if mode not in ['easy', 'medium', 'hard']:
        return jsonify({"error": "Invalid mode. Use easy, medium, or hard"}), 400

    try:
        # Get top players for this specific mode
        leaders_query = (
            Score.query
            .join(User, Score.user_id == User.id)
            .filter(Score.completed == True)
            .filter(Score.game_mode == 'mini_word_finder')
            .filter(Score.mode == mode)
            .with_entities(
                User.id,
                User.display_name,
                User.username,
                User.profile_image_data,
                User.profile_image_url,
                func.count(Score.id).label('completed_games'),
                func.min(Score.duration_sec).label('best_time'),
                func.avg(Score.duration_sec).label('avg_time'),
                func.max(Score.created_at).label('last_played')
            )
            .group_by(User.id, User.display_name, User.username, User.profile_image_data, User.profile_image_url)
            .having(func.count(Score.id) >= 1)
            .order_by('best_time', desc('completed_games'))
            .limit(25)
            .all()
        )

        leaderboard_data = []
        for leader in leaders_query:
            best_minutes = int(leader.best_time // 60) if leader.best_time else 0
            best_seconds = int(leader.best_time % 60) if leader.best_time else 0
            avg_minutes = int(leader.avg_time // 60) if leader.avg_time else 0
            avg_seconds = int(leader.avg_time % 60) if leader.avg_time else 0

            leaderboard_data.append({
                "user_id": leader.id,
                "name": leader.display_name or leader.username,
                "avatar": leader.profile_image_data or leader.profile_image_url,
                "completed_games": leader.completed_games,
                "best_time": f"{best_minutes}:{best_seconds:02d}",
                "avg_time": f"{avg_minutes}:{avg_seconds:02d}",
                "last_played": leader.last_played.strftime('%Y-%m-%d') if leader.last_played else None
            })

        return jsonify({
            "leaders": leaderboard_data,
            "mode": mode.capitalize(),
            "total": len(leaderboard_data)
        })

    except Exception as e:
        return jsonify({"error": str(e), "leaders": []}), 500

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