"""
Game Usage Tracker - Daily game usage tracking system
Based on SoulBridge AI CreativeUsageTracker pattern
"""

import sqlite3
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any

# Try to import timezone handling (prefer zoneinfo, fallback to pytz)
try:
    from zoneinfo import ZoneInfo
    ZONEINFO_AVAILABLE = True
    PYTZ_AVAILABLE = False
except ImportError:
    ZONEINFO_AVAILABLE = False
    try:
        import pytz
        PYTZ_AVAILABLE = True
    except ImportError:
        PYTZ_AVAILABLE = False

logger = logging.getLogger(__name__)

class GameUsageTracker:
    """Track daily usage of game features with Eastern Time resets"""

    def __init__(self, db_path: str = "instance/local.db"):
        self.db_path = db_path
        self.ensure_table_exists()

    def ensure_table_exists(self):
        """Create feature_usage table if it doesn't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feature_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    feature_name TEXT NOT NULL,
                    usage_date DATE NOT NULL DEFAULT (DATE('now')),
                    usage_count INTEGER NOT NULL DEFAULT 1,
                    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feature_usage_lookup
                ON feature_usage(user_id, feature_name, usage_date)
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error creating feature_usage table: {e}")

    def get_est_date(self) -> date:
        """Get current date in Eastern Time (resets at midnight EST)"""
        try:
            if ZONEINFO_AVAILABLE:
                # Use zoneinfo (Python 3.9+)
                est_tz = ZoneInfo("America/New_York")
                est_now = datetime.now(est_tz)
                return est_now.date()
            elif PYTZ_AVAILABLE:
                # Use pytz fallback
                est_tz = pytz.timezone("America/New_York")
                est_now = datetime.now(est_tz)
                return est_now.date()
            else:
                # Fallback to UTC (not ideal but functional)
                logger.warning("Using UTC date as fallback - install zoneinfo or pytz for Eastern Time")
                return datetime.utcnow().date()
        except Exception as e:
            logger.error(f"Error getting EST date: {e}")
            return datetime.utcnow().date()

    def get_usage_today(self, user_id: int, feature: str) -> int:
        """Get today's usage count for a user and feature"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            today = self.get_est_date()

            cursor.execute("""
                SELECT usage_count FROM feature_usage
                WHERE user_id = ? AND feature_name = ? AND usage_date = ?
            """, (user_id, feature, today))

            result = cursor.fetchone()
            conn.close()

            return result[0] if result else 0

        except Exception as e:
            logger.error(f"Error getting usage for {feature}: {e}")
            return 0

    def can_use_feature(self, user_id: int, feature: str, daily_limit: int = 5) -> bool:
        """Check if user can use a feature (within daily limits)"""
        try:
            # Unlimited access
            if daily_limit >= 999:
                return True

            usage_today = self.get_usage_today(user_id, feature)
            return usage_today < daily_limit

        except Exception as e:
            logger.error(f"Error checking feature usage for {feature}: {e}")
            return True  # Allow usage on error (graceful degradation)

    def record_usage(self, user_id: int, feature: str) -> bool:
        """Record usage of a feature - INCREMENTS BY 1"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            today = self.get_est_date()
            now = datetime.now()

            # Check if record exists for today
            cursor.execute("""
                SELECT usage_count FROM feature_usage
                WHERE user_id = ? AND feature_name = ? AND usage_date = ?
            """, (user_id, feature, today))

            result = cursor.fetchone()

            if result:
                # UPDATE: Increment existing record by 1
                new_count = result[0] + 1
                cursor.execute("""
                    UPDATE feature_usage
                    SET usage_count = ?, last_used_at = ?
                    WHERE user_id = ? AND feature_name = ? AND usage_date = ?
                """, (new_count, now, user_id, feature, today))
            else:
                # INSERT: Create new record with count = 1
                cursor.execute("""
                    INSERT INTO feature_usage (user_id, feature_name, usage_date, usage_count, last_used_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, feature, today, 1, now))

            conn.commit()
            conn.close()

            logger.info(f"Recorded usage: user {user_id} used {feature}")
            return True

        except Exception as e:
            logger.error(f"Error recording usage for {feature}: {e}")
            return False  # Don't block feature usage on tracking failure

    def get_usage_stats(self, user_id: int, feature: str, days: int = 7) -> Dict[str, Any]:
        """Get usage statistics for a user over specified days"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT usage_date, usage_count
                FROM feature_usage
                WHERE user_id = ? AND feature_name = ?
                AND usage_date >= DATE('now', '-{} days')
                ORDER BY usage_date DESC
            """.format(days), (user_id, feature))

            results = cursor.fetchall()
            conn.close()

            return {
                "success": True,
                "daily_usage": [{"date": row[0], "count": row[1]} for row in results],
                "total_usage": sum(row[1] for row in results)
            }

        except Exception as e:
            logger.error(f"Error getting usage stats for {feature}: {e}")
            return {"success": False, "error": str(e)}

    def reset_usage_for_user(self, user_id: int, feature: str = None) -> bool:
        """Reset usage for a user (admin function)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            today = self.get_est_date()

            if feature:
                # Reset specific feature
                cursor.execute("""
                    DELETE FROM feature_usage
                    WHERE user_id = ? AND feature_name = ? AND usage_date = ?
                """, (user_id, feature, today))
            else:
                # Reset all features for today
                cursor.execute("""
                    DELETE FROM feature_usage
                    WHERE user_id = ? AND usage_date = ?
                """, (user_id, today))

            conn.commit()
            conn.close()

            logger.info(f"Reset usage for user {user_id}, feature: {feature or 'all'}")
            return True

        except Exception as e:
            logger.error(f"Error resetting usage: {e}")
            return False