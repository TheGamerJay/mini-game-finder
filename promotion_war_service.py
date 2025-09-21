"""
Promotion War Service Module
Implements strategic promotion war system with winner/loser consequences
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import and_, or_
from models import (
    db, User, Post, PromotionWar, WarEvent, UserDebuff, UserDiscount,
    PostBoost, CreditTxn
)
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class PromotionWarService:
    """Service for managing promotion wars with strategic consequences"""

    # War configuration
    WAR_DURATION_HOURS = 1
    ACCEPTANCE_TIMEOUT_HOURS = 1

    # Winner benefits (24 hours)
    WINNER_BENEFITS = {
        'EXTENDED_PROMOTION': 2.0,     # Posts stay promoted 2x longer
        'PENALTY_IMMUNITY': True,      # Cannot receive promotion penalties
        'PROMOTION_DISCOUNT': 0.8,     # Next 3 promotions cost 8 credits (not 10)
        'PRIORITY_BOOST': 1.2,         # Posts get slight ranking boost
        'DISCOUNT_USES': 3             # Number of discounted promotions
    }

    # Loser penalties (24 hours)
    LOSER_PENALTIES = {
        'PROMOTION_COOLDOWN': 2,       # 2-hour lockout from promoting posts
        'REDUCED_EFFECTIVENESS': 0.7,  # Promotions give 7 points instead of 10
        'HIGHER_COSTS': 1.2,          # Promotions cost 12 credits instead of 10
        'LOWER_PRIORITY': 0.8         # Posts get slight ranking reduction
    }

    @staticmethod
    def challenge_user(challenger_id: int, challenged_id: int) -> Dict[str, Any]:
        """Challenge another user to a promotion war"""
        try:
            # Validate users exist
            challenger = User.query.get(challenger_id)
            challenged = User.query.get(challenged_id)

            if not challenger or not challenged:
                return {'success': False, 'error': 'Invalid users'}

            if challenger_id == challenged_id:
                return {'success': False, 'error': 'Cannot challenge yourself'}

            # Check if challenger has active war penalties
            if PromotionWarService._has_active_debuff(challenger_id, 'PROMOTION_COOLDOWN'):
                return {'success': False, 'error': 'You are in promotion cooldown from losing a recent war'}

            # Check for existing pending war between these users
            existing_war = PromotionWar.query.filter(
                and_(
                    or_(
                        and_(PromotionWar.challenger_user_id == challenger_id, PromotionWar.challenged_user_id == challenged_id),
                        and_(PromotionWar.challenger_user_id == challenged_id, PromotionWar.challenged_user_id == challenger_id)
                    ),
                    PromotionWar.status.in_(['pending', 'accepted', 'active'])
                )
            ).first()

            if existing_war:
                return {'success': False, 'error': 'War already exists between these users'}

            # Create new war
            war = PromotionWar(
                challenger_user_id=challenger_id,
                challenged_user_id=challenged_id,
                status='pending'
            )

            db.session.add(war)
            db.session.commit()

            logger.info(f"Promotion war {war.id} created: {challenger_id} challenged {challenged_id}")

            return {
                'success': True,
                'war_id': war.id,
                'message': f'Challenge sent to {challenged.display_name or challenged.username}!'
            }

        except Exception as e:
            logger.error(f"Error creating promotion war challenge: {e}")
            db.session.rollback()
            return {'success': False, 'error': 'Failed to create war challenge'}

    @staticmethod
    def accept_war(war_id: int, user_id: int) -> Dict[str, Any]:
        """Accept a promotion war challenge"""
        try:
            war = PromotionWar.query.get(war_id)

            if not war:
                return {'success': False, 'error': 'War not found'}

            if war.challenged_user_id != user_id:
                return {'success': False, 'error': 'Not authorized to accept this war'}

            if war.status != 'pending':
                return {'success': False, 'error': 'War is no longer pending'}

            # Check if challenge has expired
            if war.created_at < datetime.utcnow() - timedelta(hours=PromotionWarService.ACCEPTANCE_TIMEOUT_HOURS):
                war.status = 'expired'
                db.session.commit()
                return {'success': False, 'error': 'War challenge has expired'}

            # Start the war
            now = datetime.utcnow()
            war.status = 'active'
            war.starts_at = now
            war.ends_at = now + timedelta(hours=PromotionWarService.WAR_DURATION_HOURS)

            db.session.commit()

            logger.info(f"Promotion war {war.id} accepted and started")

            return {
                'success': True,
                'war_id': war.id,
                'ends_at': war.ends_at,
                'message': 'War accepted! You have 1 hour to accumulate promotion points.'
            }

        except Exception as e:
            logger.error(f"Error accepting promotion war: {e}")
            db.session.rollback()
            return {'success': False, 'error': 'Failed to accept war'}

    @staticmethod
    def decline_war(war_id: int, user_id: int) -> Dict[str, Any]:
        """Decline a promotion war challenge"""
        try:
            war = PromotionWar.query.get(war_id)

            if not war:
                return {'success': False, 'error': 'War not found'}

            if war.challenged_user_id != user_id:
                return {'success': False, 'error': 'Not authorized to decline this war'}

            if war.status != 'pending':
                return {'success': False, 'error': 'War is no longer pending'}

            war.status = 'declined'
            db.session.commit()

            logger.info(f"Promotion war {war.id} declined")

            return {'success': True, 'message': 'War challenge declined'}

        except Exception as e:
            logger.error(f"Error declining promotion war: {e}")
            db.session.rollback()
            return {'success': False, 'error': 'Failed to decline war'}

    @staticmethod
    def record_promotion_during_war(user_id: int, post_id: int, points_earned: int, credits_spent: int) -> None:
        """Record a promotion action during an active war"""
        try:
            # Find active war for this user
            active_war = PromotionWar.query.filter(
                and_(
                    or_(
                        PromotionWar.challenger_user_id == user_id,
                        PromotionWar.challenged_user_id == user_id
                    ),
                    PromotionWar.status == 'active',
                    PromotionWar.ends_at > datetime.utcnow()
                )
            ).first()

            if not active_war:
                return  # No active war, nothing to record

            # Record war event
            war_event = WarEvent(
                war_id=active_war.id,
                user_id=user_id,
                post_id=post_id,
                action='promote',
                points_earned=points_earned,
                credits_spent=credits_spent
            )

            db.session.add(war_event)

            # Update war scores
            if active_war.challenger_user_id == user_id:
                active_war.challenger_score += points_earned
            else:
                active_war.challenged_score += points_earned

            db.session.commit()

            logger.info(f"Recorded promotion in war {active_war.id}: user {user_id} earned {points_earned} points")

        except Exception as e:
            logger.error(f"Error recording promotion during war: {e}")
            db.session.rollback()

    @staticmethod
    def finalize_expired_wars() -> None:
        """Finalize all expired wars and apply winner/loser effects"""
        try:
            # Find all active wars that have expired
            expired_wars = PromotionWar.query.filter(
                and_(
                    PromotionWar.status == 'active',
                    PromotionWar.ends_at <= datetime.utcnow()
                )
            ).all()

            for war in expired_wars:
                PromotionWarService._finalize_war(war)

            if expired_wars:
                db.session.commit()
                logger.info(f"Finalized {len(expired_wars)} expired promotion wars")

        except Exception as e:
            logger.error(f"Error finalizing expired wars: {e}")
            db.session.rollback()

    @staticmethod
    def _finalize_war(war: PromotionWar) -> None:
        """Finalize a single war and apply consequences"""
        try:
            war.status = 'completed'

            # Determine winner and loser
            if war.challenger_score > war.challenged_score:
                winner_id = war.challenger_user_id
                loser_id = war.challenged_user_id
            elif war.challenged_score > war.challenger_score:
                winner_id = war.challenged_user_id
                loser_id = war.challenger_user_id
            else:
                # Tie - no winner/loser effects
                logger.info(f"War {war.id} ended in a tie")
                return

            war.winner_user_id = winner_id
            war.loser_user_id = loser_id

            # Apply winner benefits
            PromotionWarService._apply_winner_benefits(winner_id, war.id)

            # Apply loser penalties
            PromotionWarService._apply_loser_penalties(loser_id, war.id)

            # Update user war stats
            winner = User.query.get(winner_id)
            if winner:
                winner.war_wins = (winner.war_wins or 0) + 1

            logger.info(f"War {war.id} finalized: winner={winner_id}, loser={loser_id}")

        except Exception as e:
            logger.error(f"Error finalizing war {war.id}: {e}")
            raise

    @staticmethod
    def _apply_winner_benefits(user_id: int, war_id: int) -> None:
        """Apply 24-hour winner benefits"""
        expires_at = datetime.utcnow() + timedelta(hours=24)

        benefits = [
            UserDiscount(
                user_id=user_id,
                type='EXTENDED_PROMOTION',
                value=PromotionWarService.WINNER_BENEFITS['EXTENDED_PROMOTION'],
                expires_at=expires_at,
                war_id=war_id
            ),
            UserDiscount(
                user_id=user_id,
                type='PENALTY_IMMUNITY',
                value=1.0,
                expires_at=expires_at,
                war_id=war_id
            ),
            UserDiscount(
                user_id=user_id,
                type='PROMOTION_DISCOUNT',
                value=PromotionWarService.WINNER_BENEFITS['PROMOTION_DISCOUNT'],
                uses_remaining=PromotionWarService.WINNER_BENEFITS['DISCOUNT_USES'],
                expires_at=expires_at,
                war_id=war_id
            ),
            UserDiscount(
                user_id=user_id,
                type='PRIORITY_BOOST',
                value=PromotionWarService.WINNER_BENEFITS['PRIORITY_BOOST'],
                expires_at=expires_at,
                war_id=war_id
            )
        ]

        for benefit in benefits:
            db.session.add(benefit)

    @staticmethod
    def _apply_loser_penalties(user_id: int, war_id: int) -> None:
        """Apply 24-hour loser penalties"""
        expires_at = datetime.utcnow() + timedelta(hours=24)
        cooldown_until = datetime.utcnow() + timedelta(hours=PromotionWarService.LOSER_PENALTIES['PROMOTION_COOLDOWN'])

        penalties = [
            UserDebuff(
                user_id=user_id,
                type='PROMOTION_COOLDOWN',
                severity=1.0,
                expires_at=cooldown_until,
                war_id=war_id
            ),
            UserDebuff(
                user_id=user_id,
                type='REDUCED_EFFECTIVENESS',
                severity=PromotionWarService.LOSER_PENALTIES['REDUCED_EFFECTIVENESS'],
                expires_at=expires_at,
                war_id=war_id
            ),
            UserDebuff(
                user_id=user_id,
                type='HIGHER_COSTS',
                severity=PromotionWarService.LOSER_PENALTIES['HIGHER_COSTS'],
                expires_at=expires_at,
                war_id=war_id
            ),
            UserDebuff(
                user_id=user_id,
                type='LOWER_PRIORITY',
                severity=PromotionWarService.LOSER_PENALTIES['LOWER_PRIORITY'],
                expires_at=expires_at,
                war_id=war_id
            )
        ]

        for penalty in penalties:
            db.session.add(penalty)

    @staticmethod
    def get_user_war_status(user_id: int) -> Dict[str, Any]:
        """Get current war status and effects for a user"""
        try:
            # Check for active wars
            active_war = PromotionWar.query.filter(
                and_(
                    or_(
                        PromotionWar.challenger_user_id == user_id,
                        PromotionWar.challenged_user_id == user_id
                    ),
                    PromotionWar.status == 'active',
                    PromotionWar.ends_at > datetime.utcnow()
                )
            ).first()

            # Check for pending wars (where user is challenged)
            pending_wars = PromotionWar.query.filter(
                and_(
                    PromotionWar.challenged_user_id == user_id,
                    PromotionWar.status == 'pending',
                    PromotionWar.created_at > datetime.utcnow() - timedelta(hours=PromotionWarService.ACCEPTANCE_TIMEOUT_HOURS)
                )
            ).all()

            # Get active benefits and penalties
            now = datetime.utcnow()
            active_benefits = UserDiscount.query.filter(
                and_(
                    UserDiscount.user_id == user_id,
                    UserDiscount.expires_at > now,
                    or_(
                        UserDiscount.uses_remaining.is_(None),
                        UserDiscount.uses_remaining > 0
                    )
                )
            ).all()

            active_penalties = UserDebuff.query.filter(
                and_(
                    UserDebuff.user_id == user_id,
                    UserDebuff.expires_at > now
                )
            ).all()

            return {
                'active_war': {
                    'id': active_war.id,
                    'opponent_id': active_war.challenged_user_id if active_war.challenger_user_id == user_id else active_war.challenger_user_id,
                    'my_score': active_war.challenger_score if active_war.challenger_user_id == user_id else active_war.challenged_score,
                    'opponent_score': active_war.challenged_score if active_war.challenger_user_id == user_id else active_war.challenger_score,
                    'ends_at': active_war.ends_at
                } if active_war else None,
                'pending_challenges': [
                    {
                        'id': war.id,
                        'challenger_id': war.challenger_user_id,
                        'created_at': war.created_at
                    } for war in pending_wars
                ],
                'active_benefits': [
                    {
                        'type': benefit.type,
                        'value': benefit.value,
                        'uses_remaining': benefit.uses_remaining,
                        'expires_at': benefit.expires_at
                    } for benefit in active_benefits
                ],
                'active_penalties': [
                    {
                        'type': penalty.type,
                        'severity': penalty.severity,
                        'expires_at': penalty.expires_at
                    } for penalty in active_penalties
                ]
            }

        except Exception as e:
            logger.error(f"Error getting user war status: {e}")
            return {'error': 'Failed to get war status'}

    @staticmethod
    def get_promotion_cost(user_id: int, base_cost: int = 10) -> int:
        """Calculate actual promotion cost considering user discounts/penalties"""
        try:
            now = datetime.utcnow()

            # Check for discount
            discount = UserDiscount.query.filter(
                and_(
                    UserDiscount.user_id == user_id,
                    UserDiscount.type == 'PROMOTION_DISCOUNT',
                    UserDiscount.expires_at > now,
                    or_(
                        UserDiscount.uses_remaining.is_(None),
                        UserDiscount.uses_remaining > 0
                    )
                )
            ).first()

            # Check for penalty
            penalty = UserDebuff.query.filter(
                and_(
                    UserDebuff.user_id == user_id,
                    UserDebuff.type == 'HIGHER_COSTS',
                    UserDebuff.expires_at > now
                )
            ).first()

            final_cost = base_cost

            if discount:
                final_cost = int(base_cost * discount.value)
            elif penalty:
                final_cost = int(base_cost * penalty.severity)

            return final_cost

        except Exception as e:
            logger.error(f"Error calculating promotion cost: {e}")
            return base_cost

    @staticmethod
    def get_promotion_effectiveness(user_id: int, base_points: int = 10) -> int:
        """Calculate actual promotion points considering user penalties"""
        try:
            penalty = UserDebuff.query.filter(
                and_(
                    UserDebuff.user_id == user_id,
                    UserDebuff.type == 'REDUCED_EFFECTIVENESS',
                    UserDebuff.expires_at > datetime.utcnow()
                )
            ).first()

            if penalty:
                return int(base_points * penalty.severity)

            return base_points

        except Exception as e:
            logger.error(f"Error calculating promotion effectiveness: {e}")
            return base_points

    @staticmethod
    def _has_active_debuff(user_id: int, debuff_type: str) -> bool:
        """Check if user has an active debuff of given type"""
        return UserDebuff.query.filter(
            and_(
                UserDebuff.user_id == user_id,
                UserDebuff.type == debuff_type,
                UserDebuff.expires_at > datetime.utcnow()
            )
        ).first() is not None

    @staticmethod
    def use_discount(user_id: int, discount_type: str) -> bool:
        """Use one instance of a limited-use discount"""
        try:
            discount = UserDiscount.query.filter(
                and_(
                    UserDiscount.user_id == user_id,
                    UserDiscount.type == discount_type,
                    UserDiscount.expires_at > datetime.utcnow(),
                    UserDiscount.uses_remaining > 0
                )
            ).first()

            if discount:
                discount.uses_remaining -= 1
                db.session.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"Error using discount: {e}")
            db.session.rollback()
            return False