"""
Wars Finish Task - Close expired wars and award winners with penalty system
"""
from datetime import datetime, timedelta
from models import db, BoostWar, Post, User, BoostWarAction
from services.war_badges import record_war_win
import logging

logger = logging.getLogger(__name__)

PENALTY_HOURS = 24  # 24 hour penalty for losers

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
            logger.info(f"Processing expired war {war.id}")

            # Count actions during the war for each participant
            challenger_actions = BoostWarAction.query.filter_by(
                war_id=war.id,
                actor_user_id=war.challenger_user_id
            ).all()

            challenged_actions = BoostWarAction.query.filter_by(
                war_id=war.id,
                actor_user_id=war.challenged_user_id
            ).all()

            # Count boost vs unboost actions
            challenger_boosts = len([a for a in challenger_actions if a.action == "boost"])
            challenger_unboosts = len([a for a in challenger_actions if a.action == "unboost"])

            challenged_boosts = len([a for a in challenged_actions if a.action == "boost"])
            challenged_unboosts = len([a for a in challenged_actions if a.action == "unboost"])

            # Calculate net scores (boosts - unboosts received)
            challenger_net_score = challenger_boosts - challenged_unboosts
            challenged_net_score = challenged_boosts - challenger_unboosts

            # Store final scores
            war.challenger_final_score = challenger_net_score
            war.challenged_final_score = challenged_net_score

            # Determine winner and apply consequences
            penalty_until = datetime.utcnow() + timedelta(hours=PENALTY_HOURS)

            if challenger_net_score > challenged_net_score:
                # Challenger (Booster) wins
                war.winner_user_id = war.challenger_user_id

                # Apply net boost difference to the challenged post
                if war.challenged_post_id:
                    challenged_post = Post.query.get(war.challenged_post_id)
                    if challenged_post:
                        net_boost = challenger_net_score - challenged_net_score
                        challenged_post.boost_score = (challenged_post.boost_score or 0) + net_boost
                        logger.info(f"War {war.id}: Added {net_boost} boost to post {war.challenged_post_id}")

                # Penalty: Challenger gets 24hr challenge penalty
                challenger_user = User.query.get(war.challenged_user_id)
                if challenger_user:
                    challenger_user.challenge_penalty_until = penalty_until
                    logger.info(f"War {war.id}: Applied 24hr challenge penalty to user {war.challenged_user_id}")

            elif challenged_net_score > challenger_net_score:
                # Challenger (Unbooster) wins
                war.winner_user_id = war.challenged_user_id

                # Post boost goes to zero and gets 24hr cooldown
                if war.challenger_post_id:
                    challenger_post = Post.query.get(war.challenger_post_id)
                    if challenger_post:
                        challenger_post.boost_score = 0
                        challenger_post.boost_cooldown_until = penalty_until
                        logger.info(f"War {war.id}: Reset post {war.challenger_post_id} boost to 0 with 24hr cooldown")

                # Penalty: Booster gets 24hr boost penalty
                booster_user = User.query.get(war.challenger_user_id)
                if booster_user:
                    booster_user.boost_penalty_until = penalty_until
                    logger.info(f"War {war.id}: Applied 24hr boost penalty to user {war.challenger_user_id}")

            else:
                # Tie - no winner, no penalties
                war.winner_user_id = None
                logger.info(f"War {war.id}: Ended in tie ({challenger_net_score}-{challenged_net_score})")

            # Award badge to winner
            if war.winner_user_id:
                try:
                    record_war_win(war.winner_user_id)
                    logger.info(f"War {war.id}: User {war.winner_user_id} won and received war badge")
                except Exception as e:
                    logger.error(f"Error awarding badge to user {war.winner_user_id}: {e}")

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