"""
Redis-based leaderboard service with weekly seasons
Based on SoulBridge AI guide for scalable gaming leaderboards
"""
import os, time, hmac, hashlib, json, math, datetime
from typing import Optional, Dict, List, Any
import redis

class LeaderboardService:
    def __init__(self):
        # Use existing Redis configuration
        redis_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis.ping()
            self.redis_available = True
        except:
            self.redis = None
            self.redis_available = False
            print("Warning: Redis not available, leaderboard will use fallback mode")
        self.secret = os.getenv("LEADERBOARD_SECRET", "soulbridge-ai-secret-change-me")
        self.allow_dev_unsigned = os.getenv("ALLOW_DEV_UNSIGNED", "true").lower() == "true"

    def iso_week_season(self, dt: Optional[datetime.datetime] = None) -> str:
        """Season id like 2025-W38 (weekly)."""
        dt = dt or datetime.datetime.utcnow()
        year, week, _ = dt.isocalendar()
        return f"{year}-W{week:02d}"

    def key_lb(self, game_code: str, season_id: Optional[str] = None) -> str:
        """ZSET key for leaderboard: user_id -> score"""
        season_id = season_id or self.iso_week_season()
        return f"lb:{game_code}:{season_id}"

    def key_user(self, game_code: str, season_id: Optional[str] = None) -> str:
        """HASH key for user display names"""
        season_id = season_id or self.iso_week_season()
        return f"user:{game_code}:{season_id}"

    def key_best(self, game_code: str) -> str:
        """HASH key for all-time best scores"""
        return f"best:{game_code}"

    def key_meta(self, game_code: str) -> str:
        """HASH key for metadata"""
        return f"meta:{game_code}"

    def verify_signature(self, user_id: str, game_code: str, score: int, ts: int, signature: str) -> bool:
        """Verify HMAC signature"""
        msg = f"{user_id}|{game_code}|{score}|{ts}".encode()
        expected = hmac.new(self.secret.encode(), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def generate_signature(self, user_id: str, game_code: str, score: int, ts: int) -> str:
        """Generate HMAC signature for score submission"""
        msg = f"{user_id}|{game_code}|{score}|{ts}".encode()
        return hmac.new(self.secret.encode(), msg, hashlib.sha256).hexdigest()

    def clamp_int(self, val: Any, lo: int, hi: int, default: int) -> int:
        """Clamp integer value within bounds"""
        try:
            x = int(val)
            return max(lo, min(hi, x))
        except:
            return default

    def submit_score(self, user_id: str, display_name: str, game_code: str, score: int,
                    ts: Optional[int] = None, sig: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit a score to the leaderboard
        Returns: {"ok": bool, "season_id": str, "rank": int, "best_season": int, "best_all_time": int}
        """
        if not self.redis_available:
            return {
                "ok": True,
                "season_id": self.iso_week_season(),
                "rank": 1,
                "best_season": score,
                "best_all_time": score,
                "fallback": True
            }
        # Validation
        user_id = str(user_id).strip()
        display_name = str(display_name).strip()[:32] or "Player"
        game_code = str(game_code).strip()

        try:
            score = int(score)
        except:
            return {"ok": False, "error": "invalid_score"}

        # Signature verification
        now = int(time.time())
        if not self.allow_dev_unsigned:
            if not ts or not sig:
                return {"ok": False, "error": "missing_signature"}
            if abs(now - ts) > 600:  # 10 minutes
                return {"ok": False, "error": "stale_timestamp"}
            if not self.verify_signature(user_id, game_code, score, ts, sig):
                return {"ok": False, "error": "bad_signature"}

        # Keys
        season_id = self.iso_week_season()
        zkey = self.key_lb(game_code, season_id)
        ukey = self.key_user(game_code, season_id)
        bkey = self.key_best(game_code)

        pipe = self.redis.pipeline()

        # Set display name
        pipe.hset(ukey, user_id, display_name)

        # Only keep best score in this season
        current = self.redis.zscore(zkey, user_id)
        if current is None or score > int(current):
            pipe.zadd(zkey, {user_id: score})

        # All-time best
        current_best = self.redis.hget(bkey, user_id)
        if current_best is None or score > int(current_best):
            pipe.hset(bkey, user_id, score)

        # Metadata
        pipe.hsetnx(self.key_meta(game_code), "created_at", now)
        pipe.hset(self.key_meta(game_code), "updated_at", now)

        pipe.execute()

        # Get current rank and scores
        rank = self.redis.zrevrank(zkey, user_id)
        best_season = self.redis.zscore(zkey, user_id)
        best_all = self.redis.hget(bkey, user_id)

        return {
            "ok": True,
            "season_id": season_id,
            "rank": (rank + 1) if rank is not None else None,
            "best_season": int(best_season) if best_season is not None else None,
            "best_all_time": int(best_all) if best_all is not None else None
        }

    def get_top_scores(self, game_code: str, n: int = 10, season_id: Optional[str] = None) -> Dict[str, Any]:
        """Get top N scores for a game"""
        if not self.redis_available:
            return {
                "ok": True,
                "season_id": self.iso_week_season(),
                "count": 0,
                "rows": [],
                "fallback": True
            }

        n = self.clamp_int(n, 1, 200, 10)
        season_id = season_id or self.iso_week_season()

        zkey = self.key_lb(game_code, season_id)
        ukey = self.key_user(game_code, season_id)

        rows = self.redis.zrevrange(zkey, 0, n - 1, withscores=True)
        names = self.redis.hgetall(ukey)

        data = []
        for idx, (uid, sc) in enumerate(rows, start=1):
            data.append({
                "rank": idx,
                "user_id": uid,
                "display_name": names.get(uid, "Player"),
                "score": int(sc)
            })

        return {"ok": True, "season_id": season_id, "count": len(data), "rows": data}

    def get_around_user(self, game_code: str, user_id: str, window: int = 3,
                       season_id: Optional[str] = None) -> Dict[str, Any]:
        """Get scores around a specific user"""
        if not self.redis_available:
            return {
                "ok": True,
                "season_id": self.iso_week_season(),
                "present": False,
                "rows": [],
                "fallback": True
            }

        season_id = season_id or self.iso_week_season()
        window = self.clamp_int(window, 1, 10, 3)

        zkey = self.key_lb(game_code, season_id)
        ukey = self.key_user(game_code, season_id)

        rank = self.redis.zrevrank(zkey, user_id)
        if rank is None:
            return {"ok": True, "season_id": season_id, "present": False, "rows": []}

        start = max(0, rank - window)
        end = rank + window

        rows = self.redis.zrevrange(zkey, start, end, withscores=True)
        names = self.redis.hgetall(ukey)

        out = []
        for idx, (uid, sc) in enumerate(rows, start=start+1):
            out.append({
                "rank": idx,
                "user_id": uid,
                "display_name": names.get(uid, "Player"),
                "score": int(sc),
                "me": (uid == user_id)
            })

        return {"ok": True, "season_id": season_id, "present": True, "rows": out}

    def get_user_rank(self, game_code: str, user_id: str, season_id: Optional[str] = None) -> Dict[str, Any]:
        """Get rank and score for a specific user"""
        if not self.redis_available:
            return {
                "ok": True,
                "season_id": self.iso_week_season(),
                "rank": None,
                "score": None,
                "fallback": True
            }

        season_id = season_id or self.iso_week_season()

        zkey = self.key_lb(game_code, season_id)
        rank = self.redis.zrevrank(zkey, user_id)
        score = self.redis.zscore(zkey, user_id)

        return {
            "ok": True,
            "season_id": season_id,
            "rank": (rank + 1) if rank is not None else None,
            "score": int(score) if score is not None else None
        }

    def get_user_best(self, game_code: str, user_id: str) -> Dict[str, Any]:
        """Get user's all-time best score"""
        if not self.redis_available:
            return {
                "ok": True,
                "best_all_time": None,
                "fallback": True
            }

        bkey = self.key_best(game_code)
        best = self.redis.hget(bkey, user_id)

        return {
            "ok": True,
            "best_all_time": int(best) if best is not None else None
        }

    def register_game(self, game_code: str):
        """Register a game for seasonal rotation"""
        self.redis.sadd("games", game_code)

# Global instance
leaderboard_service = LeaderboardService()