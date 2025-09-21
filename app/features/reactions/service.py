"""Business logic for reactions feature."""
from typing import List

from sqlalchemy.exc import IntegrityError
from psycopg2 import errors as pg_errors

from app.common.errors import ValidationError, NotFound
from app.common.logging import get_feature_logger
from app.features.reactions.dto import (
    GetReactionsInput,
    GetReactionsResult,
    PostReactionsData,
    ReactOnceInput,
    ReactOnceResult,
)
from app.features.reactions.repo import ReactionsRepo

logger = get_feature_logger("reactions")

# Valid reaction types
VALID_REACTIONS = ["love", "magic", "peace", "fire", "gratitude", "star", "applause", "support"]


class ReactionsService:
    """Business logic for reactions."""

    def __init__(self, repo: ReactionsRepo) -> None:
        """Initialize with repository."""
        self.repo = repo

    def react_once(self, input_data: ReactOnceInput) -> ReactOnceResult:
        """
        Create a single reaction with proper business rules.

        Implements the "insert once, then show message" flow with race condition handling.
        """
        # Validate reaction type
        if input_data.reaction_type not in VALID_REACTIONS:
            raise ValidationError(
                f"Invalid reaction type: {input_data.reaction_type}",
                details={"valid_reactions": VALID_REACTIONS},
            )

        logger.info(
            "Attempting to create reaction",
            extra={
                "post_id": input_data.post_id,
                "user_id": input_data.user_id,
                "reaction_type": input_data.reaction_type,
            },
        )

        # Check if user already reacted (for friendly message with actual emoji)
        existing = self.repo.get_user_reaction(input_data.post_id, input_data.user_id)
        if existing:
            logger.info(
                "User already reacted to post",
                extra={
                    "post_id": input_data.post_id,
                    "user_id": input_data.user_id,
                    "existing_reaction": existing.reaction_type,
                    "attempted_reaction": input_data.reaction_type,
                },
            )
            return ReactOnceResult.already_exists(existing.reaction_type)

        # TODO: Add business rules here such as:
        # - Check if post exists (would require coordination with posts feature)
        # - Check if user is allowed to react (rate limiting, bans, etc.)
        # - Log analytics events

        try:
            # Insert the reaction
            self.repo.insert_reaction(
                input_data.post_id, input_data.user_id, input_data.reaction_type
            )

            logger.info(
                "Reaction created successfully",
                extra={
                    "post_id": input_data.post_id,
                    "user_id": input_data.user_id,
                    "reaction_type": input_data.reaction_type,
                },
            )

            return ReactOnceResult.success(input_data.reaction_type)

        except IntegrityError as e:
            # Handle race condition: someone else inserted between our SELECT and INSERT
            if isinstance(getattr(e, "orig", None), pg_errors.UniqueViolation):
                logger.info(
                    "Race condition detected in reaction creation",
                    extra={
                        "post_id": input_data.post_id,
                        "user_id": input_data.user_id,
                        "reaction_type": input_data.reaction_type,
                    },
                )

                # Query again to get the actual stored reaction
                existing = self.repo.get_user_reaction(input_data.post_id, input_data.user_id)
                reaction_type = existing.reaction_type if existing else input_data.reaction_type
                return ReactOnceResult.already_exists(reaction_type)

            # Re-raise other integrity errors
            logger.error(
                "Unexpected integrity error in reaction creation",
                extra={
                    "post_id": input_data.post_id,
                    "user_id": input_data.user_id,
                    "reaction_type": input_data.reaction_type,
                    "error": str(e),
                },
                exc_info=e,
            )
            raise

    def get_reactions(self, input_data: GetReactionsInput) -> GetReactionsResult:
        """Get reactions for multiple posts efficiently."""
        logger.info(
            "Getting reactions for posts",
            extra={
                "post_count": len(input_data.post_ids),
                "user_id": input_data.user_id,
            },
        )

        # Get reaction counts for all posts
        counts_by_post = self.repo.get_reaction_counts_bulk(input_data.post_ids)

        # Get user reactions if user is specified
        user_reactions = {}
        if input_data.user_id:
            user_reactions = self.repo.get_user_reactions_bulk(
                input_data.post_ids, input_data.user_id
            )

        # Build result
        reactions_by_post = {}
        for post_id in input_data.post_ids:
            post_reactions = PostReactionsData(
                post_id=post_id,
                reaction_counts=counts_by_post.get(post_id, []),
                user_reaction=user_reactions.get(post_id),
            )
            reactions_by_post[post_id] = post_reactions

        logger.info(
            "Retrieved reactions for posts",
            extra={
                "post_count": len(input_data.post_ids),
                "posts_with_reactions": len([p for p in reactions_by_post.values() if p.reaction_counts]),
                "user_id": input_data.user_id,
            },
        )

        return GetReactionsResult(reactions_by_post=reactions_by_post)

    def get_post_reactions(self, post_id: int, user_id: int = None) -> PostReactionsData:
        """Get reactions for a single post."""
        input_data = GetReactionsInput(post_ids=[post_id], user_id=user_id)
        result = self.get_reactions(input_data)
        return result.get_post_reactions(post_id)

    def delete_user_data(self, user_id: int) -> int:
        """Delete all reaction data for a user (GDPR compliance)."""
        logger.info("Deleting all reaction data for user", extra={"user_id": user_id})

        deleted_count = self.repo.delete_user_reactions(user_id)

        logger.info(
            "Deleted user reaction data",
            extra={"user_id": user_id, "deleted_count": deleted_count},
        )

        return deleted_count

    def delete_post_data(self, post_id: int) -> int:
        """Delete all reaction data for a post."""
        logger.info("Deleting all reaction data for post", extra={"post_id": post_id})

        deleted_count = self.repo.delete_post_reactions(post_id)

        logger.info(
            "Deleted post reaction data",
            extra={"post_id": post_id, "deleted_count": deleted_count},
        )

        return deleted_count

    def get_valid_reactions(self) -> List[str]:
        """Get list of valid reaction types."""
        return VALID_REACTIONS.copy()

    def get_reaction_statistics(self) -> dict[str, int]:
        """Get overall reaction statistics."""
        logger.info("Getting reaction statistics")
        return self.repo.get_reaction_stats()