# tasks/promotion_wars.py
from celery_app import celery
from datetime import datetime, timezone, timedelta
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

def _pg():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@celery.task(name="tasks.promotion_wars.finalize_due_wars")
def finalize_due_wars():
    """Find wars past end_time and finalize them (apply win/lose effects)."""
    now = datetime.now(timezone.utc)
    with _pg() as conn, conn.cursor() as cur:
        # Find active promotion wars that have ended
        cur.execute("""
            SELECT id, challenger_user_id, challenged_user_id, challenger_score, challenged_score
            FROM promotion_wars
            WHERE status='active' AND ends_at <= %s
            FOR UPDATE SKIP LOCKED
        """, (now,))
        wars = cur.fetchall()

        for war in wars:
            war_id = war["id"]
            challenger_id = war["challenger_user_id"]
            challenged_id = war["challenged_user_id"]
            challenger_score = war["challenger_score"]
            challenged_score = war["challenged_score"]

            # Determine winner and loser
            if challenger_score > challenged_score:
                winner_id = challenger_id
                loser_id = challenged_id
            elif challenged_score > challenger_score:
                winner_id = challenged_id
                loser_id = challenger_id
            else:
                # Tie - no winner/loser effects
                winner_id = None
                loser_id = None

            # Update war status
            cur.execute("""
                UPDATE promotion_wars
                SET status='completed', winner_user_id=%s, loser_user_id=%s, updated_at=%s
                WHERE id=%s
            """, (winner_id, loser_id, now, war_id))

            if winner_id and loser_id:
                # Apply winner benefits (24 hours)
                expires_at = now + timedelta(hours=24)

                # Winner discounts and benefits
                cur.execute("""
                    INSERT INTO user_discounts (user_id, type, value, uses_remaining, expires_at, war_id, created_at)
                    VALUES
                        (%s, 'EXTENDED_PROMOTION', 2.0, NULL, %s, %s, %s),
                        (%s, 'PENALTY_IMMUNITY', 1.0, NULL, %s, %s, %s),
                        (%s, 'PROMOTION_DISCOUNT', 0.8, 3, %s, %s, %s),
                        (%s, 'PRIORITY_BOOST', 1.2, NULL, %s, %s, %s)
                """, (
                    winner_id, expires_at, war_id, now,
                    winner_id, expires_at, war_id, now,
                    winner_id, expires_at, war_id, now,
                    winner_id, expires_at, war_id, now
                ))

                # Loser penalties (24 hours)
                cooldown_until = now + timedelta(hours=2)
                penalty_expires = now + timedelta(hours=24)

                cur.execute("""
                    INSERT INTO user_debuffs (user_id, type, severity, expires_at, war_id, created_at)
                    VALUES
                        (%s, 'PROMOTION_COOLDOWN', 1.0, %s, %s, %s),
                        (%s, 'REDUCED_EFFECTIVENESS', 0.7, %s, %s, %s),
                        (%s, 'HIGHER_COSTS', 1.2, %s, %s, %s),
                        (%s, 'LOWER_PRIORITY', 0.8, %s, %s, %s)
                """, (
                    loser_id, cooldown_until, war_id, now,
                    loser_id, penalty_expires, war_id, now,
                    loser_id, penalty_expires, war_id, now,
                    loser_id, penalty_expires, war_id, now
                ))

                # Update user war wins counter
                cur.execute("""
                    UPDATE users SET war_wins = COALESCE(war_wins, 0) + 1 WHERE id = %s
                """, (winner_id,))

        conn.commit()
    return {"finalized": len(wars)}

@celery.task(name="tasks.promotion_wars.notify_expiring_effects")
def notify_expiring_effects():
    """Notify users whose buffs/debuffs will expire soon."""
    with _pg() as conn, conn.cursor() as cur:
        # Check for expiring debuffs
        cur.execute("""
            SELECT d.user_id, d.type, d.expires_at, u.username
            FROM user_debuffs d
            JOIN users u ON d.user_id = u.id
            WHERE d.expires_at BETWEEN NOW() AND NOW() + INTERVAL '1 hour'
        """)
        debuffs = cur.fetchall()

        # Check for low discount uses
        cur.execute("""
            SELECT d.user_id, d.type, d.uses_remaining, u.username
            FROM user_discounts d
            JOIN users u ON d.user_id = u.id
            WHERE d.uses_remaining <= 1 AND d.uses_remaining > 0
              AND d.expires_at > NOW()
        """)
        discounts = cur.fetchall()

        notifications = 0

        # Create notifications for expiring debuffs
        for debuff in debuffs:
            cur.execute("""
                INSERT INTO notifications (user_id, type, message, created_at)
                VALUES (%s, 'penalty_expiring', %s, NOW())
                ON CONFLICT DO NOTHING
            """, (
                debuff["user_id"],
                f"Your {debuff['type'].lower().replace('_', ' ')} penalty will expire within 1 hour."
            ))
            notifications += 1

        # Create notifications for low discount uses
        for discount in discounts:
            cur.execute("""
                INSERT INTO notifications (user_id, type, message, created_at)
                VALUES (%s, 'discount_low', %s, NOW())
                ON CONFLICT DO NOTHING
            """, (
                discount["user_id"],
                f"You have {discount['uses_remaining']} discounted promotion{'s' if discount['uses_remaining'] != 1 else ''} remaining."
            ))
            notifications += 1

        conn.commit()
    return {"notified": notifications}