"""
Boost Decay Task - Gradually reduce boost scores over time
"""
from models import db
from sqlalchemy import text

DECAY_STEP_MIN = 18  # Decay 1 point every 18 minutes

def decay_boosts_step():
    """
    Decay boost scores by 1 point for posts that haven't been boosted recently

    This runs periodically to create natural decay in the boost system.
    Posts lose 1 boost point every DECAY_STEP_MIN minutes of inactivity.
    """
    try:
        # Update posts that are due for decay
        sql = f"""
        UPDATE posts
        SET boost_score = CASE
            WHEN boost_score > 0 THEN boost_score - 1
            ELSE 0
        END,
        last_boost_at = datetime('now')
        WHERE boost_score > 0
          AND (last_boost_at IS NULL OR
               datetime('now') >= datetime(last_boost_at, '+{DECAY_STEP_MIN} minutes'))
        """

        result = db.session.execute(text(sql))
        rows_updated = result.rowcount
        db.session.commit()

        if rows_updated > 0:
            print(f"Decayed {rows_updated} posts by 1 boost point")

        return rows_updated

    except Exception as e:
        print(f"Error in boost decay: {e}")
        db.session.rollback()
        return 0

def get_decay_info():
    """Get information about the decay system"""
    return {
        "decay_step_minutes": DECAY_STEP_MIN,
        "description": f"Posts lose 1 boost point every {DECAY_STEP_MIN} minutes of inactivity"
    }