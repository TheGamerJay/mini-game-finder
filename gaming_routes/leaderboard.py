from flask import Blueprint, jsonify
from models import User, Score, db
from sqlalchemy import func, desc, text
from utils.public import public

leaderboard_bp = Blueprint("leaderboard", __name__)

@leaderboard_bp.route("/api/leaderboard/word-finder", methods=["GET"])
@public
def word_finder_leaderboard():
    """Get Word Finder leaderboard showing top players by completion rate and speed"""
    try:
        # Use raw SQL for database compatibility
        sql = text("""
            SELECT
                u.id as user_id,
                COALESCE(u.display_name, u.username) as name,
                COALESCE(u.profile_image_data, u.profile_image_url) as avatar,
                COUNT(s.id) as completed_games,
                AVG(s.duration_sec) as avg_time,
                AVG(s.found_count * 100.0 / GREATEST(COALESCE(s.found_count, 1), 1)) as avg_completion_rate,
                MAX(s.created_at) as last_played
            FROM scores s
            JOIN users u ON s.user_id = u.id
            WHERE s.found_count > 0
                AND (s.game_mode = 'mini_word_finder' OR s.game_mode IS NULL)
            GROUP BY u.id, u.display_name, u.username, u.profile_image_data, u.profile_image_url
            HAVING COUNT(s.id) >= 3
            ORDER BY COUNT(s.id) DESC, AVG(s.duration_sec) ASC
            LIMIT 50
        """)

        result = db.session.execute(sql)
        leaders = result.fetchall()

        leaderboard_data = []
        for leader in leaders:
            avg_time = leader.avg_time or 0
            avg_minutes = int(avg_time // 60)
            avg_seconds = int(avg_time % 60)

            leaderboard_data.append({
                "user_id": leader.user_id,
                "name": leader.name,
                "avatar": leader.avatar,
                "completed_games": leader.completed_games,
                "avg_time": f"{avg_minutes}:{avg_seconds:02d}",
                "avg_completion_rate": round(leader.avg_completion_rate or 0, 1),
                "last_played": leader.last_played.strftime('%Y-%m-%d') if leader.last_played else None
            })

        return jsonify({"leaders": leaderboard_data, "total": len(leaderboard_data)})

    except Exception as e:
        return jsonify({"error": str(e), "leaders": []}), 500

@leaderboard_bp.route("/api/leaderboard/word-finder/<mode>", methods=["GET"])
@public
def word_finder_mode_leaderboard(mode):
    """Get Word Finder leaderboard for specific difficulty mode (easy/medium/hard)"""
    if mode not in ['easy', 'medium', 'hard']:
        return jsonify({"error": "Invalid mode. Use easy, medium, or hard"}), 400

    try:
        # Use raw SQL for database compatibility
        sql = text("""
            SELECT
                u.id as user_id,
                COALESCE(u.display_name, u.username) as name,
                COALESCE(u.profile_image_data, u.profile_image_url) as avatar,
                COUNT(s.id) as completed_games,
                MIN(s.duration_sec) as best_time,
                AVG(s.duration_sec) as avg_time,
                MAX(s.created_at) as last_played
            FROM scores s
            JOIN users u ON s.user_id = u.id
            WHERE s.found_count > 0
                AND (s.game_mode = 'mini_word_finder' OR s.game_mode IS NULL)
                AND s.mode = :mode
            GROUP BY u.id, u.display_name, u.username, u.profile_image_data, u.profile_image_url
            HAVING COUNT(s.id) >= 1
            ORDER BY MIN(s.duration_sec) ASC, COUNT(s.id) DESC
            LIMIT 25
        """)

        result = db.session.execute(sql, {"mode": mode})
        leaders = result.fetchall()

        leaderboard_data = []
        for leader in leaders:
            best_time = leader.best_time or 0
            avg_time = leader.avg_time or 0

            best_minutes = int(best_time // 60)
            best_seconds = int(best_time % 60)
            avg_minutes = int(avg_time // 60)
            avg_seconds = int(avg_time % 60)

            leaderboard_data.append({
                "user_id": leader.user_id,
                "name": leader.name,
                "avatar": leader.avatar,
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
@public
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