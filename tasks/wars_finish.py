"""
Wars Finish Task - Close expired wars and award winners
"""
from datetime import datetime
from models import db, BoostWar, Post
from services.war_badges import record_war_win

def close_expired_wars_and_award():
    """
    Close expired boost wars and award badges to winners

    This runs periodically to:
    1. Find wars that have reached their end time
    2. Compare final boost scores
    3. Determine winner (or tie)
    4. Award War Champion badge to winner
    5. Mark war as finished
    """
    try:
        now = datetime.utcnow()

        # Find active wars that have expired
        wars = (BoostWar.query
                .filter(BoostWar.status == "active", BoostWar.ends_at <= now)
                .all())

        wars_closed = 0

        for war in wars:
            # Get final scores from posts
            c_post = Post.query.get(war.challenger_post_id) if war.challenger_post_id else None
            d_post = Post.query.get(war.challenged_post_id) if war.challenged_post_id else None

            c_score = (c_post.boost_score if c_post else 0) or 0
            d_score = (d_post.boost_score if d_post else 0) or 0

            # Store final scores
            war.challenger_final_score = c_score
            war.challenged_final_score = d_score

            # Determine winner
            winner_user_id = None
            if c_score > d_score:
                winner_user_id = war.challenger_user_id
            elif d_score > c_score:
                winner_user_id = war.challenged_user_id
            # If tie, no winner (winner_user_id stays None)

            war.winner_user_id = winner_user_id

            # Award badge to winner
            if winner_user_id:
                try:
                    record_war_win(winner_user_id)
                    print(f"War {war.id}: User {winner_user_id} won with score {c_score if winner_user_id == war.challenger_user_id else d_score}")
                except Exception as e:
                    print(f"Error awarding badge to user {winner_user_id}: {e}")
            else:
                print(f"War {war.id}: Ended in tie ({c_score}-{d_score})")

            # Mark war as finished
            war.status = "finished"
            wars_closed += 1

        if wars_closed > 0:
            db.session.commit()
            print(f"Closed {wars_closed} expired wars")

        return wars_closed

    except Exception as e:
        print(f"Error closing wars: {e}")
        db.session.rollback()
        return 0

def get_active_wars_info():
    """Get information about active wars"""
    try:
        now = datetime.utcnow()
        active_count = BoostWar.query.filter_by(status="active").count()
        expired_count = (BoostWar.query
                        .filter(BoostWar.status == "active", BoostWar.ends_at <= now)
                        .count())

        return {
            "active_wars": active_count,
            "expired_wars": expired_count,
            "timestamp": now.isoformat()
        }
    except Exception as e:
        print(f"Error getting wars info: {e}")
        return {"error": str(e)}