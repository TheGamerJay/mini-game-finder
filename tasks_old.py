"""
Celery Tasks for Promotion War System
"""
from celery_app import celery
from datetime import datetime, timedelta
from models import db, PromotionWar, UserDebuff, UserDiscount, User
from promotion_war_service import PromotionWarService
from sqlalchemy import and_
import logging

logger = logging.getLogger(__name__)

@celery.task(name="tasks.finalize_expired_wars", bind=True)
def finalize_expired_wars(self):
    """🏆 Auto-finalize expired promotion wars"""
    try:
        # Use your existing service
        PromotionWarService.finalize_expired_wars()
        logger.info("Checked for expired promotion wars")
        return {"status": "success", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error finalizing wars: {e}")
        return {"status": "error", "error": str(e)}

@celery.task(name="tasks.cleanup_expired_effects", bind=True)
def cleanup_expired_effects(self):
    """🧹 Clean up expired debuffs and discounts"""
    try:
        now = datetime.utcnow()
        cleaned_count = 0

        # Remove expired debuffs
        expired_debuffs = UserDebuff.query.filter(UserDebuff.expires_at <= now).all()
        for debuff in expired_debuffs:
            db.session.delete(debuff)
            cleaned_count += 1

        # Remove expired discounts with no uses left
        expired_discounts = UserDiscount.query.filter(
            and_(
                UserDiscount.expires_at <= now,
                UserDiscount.uses_remaining <= 0
            )
        ).all()
        for discount in expired_discounts:
            db.session.delete(discount)
            cleaned_count += 1

        db.session.commit()

        logger.info(f"Cleaned up {cleaned_count} expired effects")
        return {"status": "success", "cleaned": cleaned_count}

    except Exception as e:
        logger.error(f"Error cleaning expired effects: {e}")
        db.session.rollback()
        return {"status": "error", "error": str(e)}

@celery.task(name="tasks.notify_expiring_penalties", bind=True)
def notify_expiring_penalties(self):
    """⚠️ Notify users about expiring penalties/benefits"""
    try:
        soon = datetime.utcnow() + timedelta(hours=1)
        now = datetime.utcnow()
        notifications_sent = 0

        # Find penalties expiring within 1 hour
        expiring_debuffs = UserDebuff.query.filter(
            and_(
                UserDebuff.expires_at <= soon,
                UserDebuff.expires_at > now
            )
        ).all()

        # Find discounts with low uses remaining
        low_discounts = UserDiscount.query.filter(
            and_(
                UserDiscount.uses_remaining <= 1,
                UserDiscount.uses_remaining > 0,
                UserDiscount.expires_at > now
            )
        ).all()

        # Send penalty expiring notifications
        for debuff in expiring_debuffs:
            user = User.query.get(debuff.user_id)
            if user:
                send_penalty_expiring_notification(user, debuff)
                notifications_sent += 1

        # Send discount low notifications
        for discount in low_discounts:
            user = User.query.get(discount.user_id)
            if user:
                send_discount_low_notification(user, discount)
                notifications_sent += 1

        logger.info(f"Sent {notifications_sent} expiration notifications")
        return {"status": "success", "notifications_sent": notifications_sent}

    except Exception as e:
        logger.error(f"Error sending notifications: {e}")
        return {"status": "error", "error": str(e)}

@celery.task(name="tasks.war_reminder_notifications", bind=True)
def war_reminder_notifications(self):
    """⏰ Send war-related reminders"""
    try:
        now = datetime.utcnow()
        reminders_sent = 0

        # Find pending wars about to expire (1 hour timeout)
        expiring_challenges = PromotionWar.query.filter(
            and_(
                PromotionWar.status == 'pending',
                PromotionWar.created_at <= now - timedelta(minutes=45),  # 15 min warning
                PromotionWar.created_at > now - timedelta(hours=1)  # Not yet expired
            )
        ).all()

        # Find active wars ending soon (15 min warning)
        ending_wars = PromotionWar.query.filter(
            and_(
                PromotionWar.status == 'active',
                PromotionWar.ends_at <= now + timedelta(minutes=15),
                PromotionWar.ends_at > now
            )
        ).all()

        for war in expiring_challenges:
            send_challenge_expiring_reminder(war)
            reminders_sent += 1

        for war in ending_wars:
            send_war_ending_reminder(war)
            reminders_sent += 1

        logger.info(f"Sent {reminders_sent} war reminders")
        return {"status": "success", "reminders_sent": reminders_sent}

    except Exception as e:
        logger.error(f"Error sending war reminders: {e}")
        return {"status": "error", "error": str(e)}

# Helper notification functions
def send_penalty_expiring_notification(user, debuff):
    """Send notification that penalty is expiring soon"""
    logger.info(f"Penalty expiring soon for user {user.id}: {debuff.type}")
    # TODO: Add actual notification logic (email, push, etc.)

def send_discount_low_notification(user, discount):
    """Send notification that discount uses are low"""
    logger.info(f"Discount almost used up for user {user.id}: {discount.uses_remaining} uses left")
    # TODO: Add actual notification logic

def send_challenge_expiring_reminder(war):
    """Remind about pending challenge expiring"""
    logger.info(f"War challenge {war.id} expiring soon")
    # TODO: Add actual notification logic

def send_war_ending_reminder(war):
    """Remind participants that war is ending soon"""
    logger.info(f"War {war.id} ending in 15 minutes")
    # TODO: Add actual notification logic