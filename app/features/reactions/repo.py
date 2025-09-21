"""Repository for reactions data access - owns post_reactions table exclusively."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.features.reactions.dto import ReactionCount, ReactionData


class ReactionsRepo:
    """Repository for reactions database operations."""

    def __init__(self, session: Session) -> None:
        """Initialize with database session."""
        self.session = session

    def get_user_reaction(self, post_id: int, user_id: int) -> Optional[ReactionData]:
        """Get a user's reaction to a specific post."""
        query = text("""
            SELECT post_id, user_id, reaction_type, created_at
            FROM post_reactions
            WHERE post_id = :post_id AND user_id = :user_id
        """)

        result = self.session.execute(query, {"post_id": post_id, "user_id": user_id}).fetchone()

        if result:
            # Parse datetime string if needed (SQLite compatibility)
            created_at = result.created_at
            if isinstance(created_at, str):
                from datetime import datetime
                created_at = datetime.fromisoformat(created_at.replace(' ', 'T'))

            return ReactionData(
                post_id=result.post_id,
                user_id=result.user_id,
                reaction_type=result.reaction_type,
                created_at=created_at,
            )
        return None

    def insert_reaction(self, post_id: int, user_id: int, reaction_type: str) -> None:
        """Insert a new reaction."""
        query = text("""
            INSERT INTO post_reactions (post_id, user_id, reaction_type, created_at)
            VALUES (:post_id, :user_id, :reaction_type, CURRENT_TIMESTAMP)
        """)

        self.session.execute(
            query, {"post_id": post_id, "user_id": user_id, "reaction_type": reaction_type}
        )

    def get_reaction_counts(self, post_id: int) -> List[ReactionCount]:
        """Get reaction counts for a post."""
        query = text("""
            SELECT reaction_type, COUNT(*) as count
            FROM post_reactions
            WHERE post_id = :post_id
            GROUP BY reaction_type
            ORDER BY reaction_type
        """)

        results = self.session.execute(query, {"post_id": post_id}).fetchall()

        return [ReactionCount(reaction_type=row.reaction_type, count=row.count) for row in results]

    def get_reaction_counts_bulk(self, post_ids: List[int]) -> dict[int, List[ReactionCount]]:
        """Get reaction counts for multiple posts efficiently."""
        if not post_ids:
            return {}

        # Use IN clause for SQLite compatibility
        placeholders = ','.join([str(pid) for pid in post_ids])
        query = text(f"""
            SELECT post_id, reaction_type, COUNT(*) as count
            FROM post_reactions
            WHERE post_id IN ({placeholders})
            GROUP BY post_id, reaction_type
            ORDER BY post_id, reaction_type
        """)

        results = self.session.execute(query).fetchall()

        # Group by post_id
        counts_by_post: dict[int, List[ReactionCount]] = {}
        for row in results:
            post_id = row.post_id
            if post_id not in counts_by_post:
                counts_by_post[post_id] = []
            counts_by_post[post_id].append(
                ReactionCount(reaction_type=row.reaction_type, count=row.count)
            )

        return counts_by_post

    def get_user_reactions_bulk(self, post_ids: List[int], user_id: int) -> dict[int, str]:
        """Get user's reactions for multiple posts."""
        if not post_ids:
            return {}

        # Use IN clause for SQLite compatibility
        placeholders = ','.join([str(pid) for pid in post_ids])
        query = text(f"""
            SELECT post_id, reaction_type
            FROM post_reactions
            WHERE post_id IN ({placeholders}) AND user_id = :user_id
        """)

        results = self.session.execute(
            query, {"user_id": user_id}
        ).fetchall()

        return {row.post_id: row.reaction_type for row in results}

    def delete_user_reactions(self, user_id: int) -> int:
        """Delete all reactions by a user (for account deletion)."""
        query = text("""
            DELETE FROM post_reactions
            WHERE user_id = :user_id
        """)

        result = self.session.execute(query, {"user_id": user_id})
        return result.rowcount if result.rowcount else 0

    def delete_post_reactions(self, post_id: int) -> int:
        """Delete all reactions for a post (for post deletion)."""
        query = text("""
            DELETE FROM post_reactions
            WHERE post_id = :post_id
        """)

        result = self.session.execute(query, {"post_id": post_id})
        return result.rowcount if result.rowcount else 0

    def get_reaction_stats(self) -> dict[str, int]:
        """Get overall reaction statistics."""
        query = text("""
            SELECT reaction_type, COUNT(*) as count
            FROM post_reactions
            GROUP BY reaction_type
            ORDER BY count DESC
        """)

        results = self.session.execute(query).fetchall()
        return {row.reaction_type: row.count for row in results}