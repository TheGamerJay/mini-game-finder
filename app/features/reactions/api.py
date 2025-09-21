"""API layer for reactions feature - handles HTTP requests and responses."""
from flask import Blueprint, request
from sqlalchemy.orm import Session

from app.common.auth import require_auth
from app.common.db import get_db_session
from app.common.errors import ValidationError
from app.common.http import ApiResponse
from app.common.logging import get_feature_logger
from app.features.reactions.dto import GetReactionsInput, ReactOnceInput
from app.features.reactions.repo import ReactionsRepo
from app.features.reactions.service import ReactionsService

logger = get_feature_logger("reactions.api")

# Create blueprint for reactions API
reactions_bp = Blueprint("reactions", __name__, url_prefix="/api/v1/reactions")


@reactions_bp.route("/react", methods=["POST"])
@require_auth
def react_once():
    """Create a single reaction (POST /api/v1/reactions/react)."""
    user_id = request.current_user.id
    data = request.get_json()

    if not data:
        return ApiResponse.error("Request body is required", 400)

    try:
        # Validate required fields
        post_id = data.get("post_id")
        reaction_type = data.get("reaction_type")

        if not post_id:
            return ApiResponse.error("post_id is required", 400)
        if not reaction_type:
            return ApiResponse.error("reaction_type is required", 400)

        # Create input DTO (validates data)
        input_data = ReactOnceInput(
            post_id=int(post_id), user_id=user_id, reaction_type=str(reaction_type)
        )

        # Process request
        with get_db_session() as session:
            repo = ReactionsRepo(session)
            service = ReactionsService(repo)
            result = service.react_once(input_data)

        # Return response
        return ApiResponse.success(
            {
                "created": result.created,
                "reaction_type": result.reaction_type,
                "message": result.message,
            }
        )

    except ValueError as e:
        logger.warning("Invalid input for reaction", extra={"error": str(e), "user_id": user_id})
        return ApiResponse.error(f"Invalid input: {str(e)}", 400)

    except ValidationError as e:
        logger.warning("Validation error for reaction", extra={"error": str(e), "user_id": user_id})
        return ApiResponse.error(str(e), 400)

    except Exception as e:
        logger.error(
            "Unexpected error in react_once",
            extra={"error": str(e), "user_id": user_id},
            exc_info=e,
        )
        return ApiResponse.error("An unexpected error occurred", 500)


@reactions_bp.route("/posts", methods=["GET"])
def get_reactions():
    """Get reactions for multiple posts (GET /api/v1/reactions/posts?post_ids=1,2,3&user_id=123)."""
    try:
        # Parse query parameters
        post_ids_param = request.args.get("post_ids", "")
        user_id_param = request.args.get("user_id")

        if not post_ids_param:
            return ApiResponse.error("post_ids parameter is required", 400)

        # Parse post_ids
        try:
            post_ids = [int(pid.strip()) for pid in post_ids_param.split(",") if pid.strip()]
        except ValueError:
            return ApiResponse.error("post_ids must be comma-separated integers", 400)

        if not post_ids:
            return ApiResponse.error("At least one post_id is required", 400)

        # Parse user_id (optional)
        user_id = None
        if user_id_param:
            try:
                user_id = int(user_id_param)
            except ValueError:
                return ApiResponse.error("user_id must be an integer", 400)

        # Create input DTO
        input_data = GetReactionsInput(post_ids=post_ids, user_id=user_id)

        # Process request
        with get_db_session() as session:
            repo = ReactionsRepo(session)
            service = ReactionsService(repo)
            result = service.get_reactions(input_data)

        # Convert to API response format
        response_data = {}
        for post_id, post_reactions in result.reactions_by_post.items():
            response_data[str(post_id)] = {
                "post_id": post_reactions.post_id,
                "total_reactions": post_reactions.total_reactions,
                "reaction_counts": [
                    {"reaction_type": rc.reaction_type, "count": rc.count}
                    for rc in post_reactions.reaction_counts
                ],
                "user_reaction": post_reactions.user_reaction,
            }

        return ApiResponse.success({"reactions_by_post": response_data})

    except ValidationError as e:
        logger.warning("Validation error for get_reactions", extra={"error": str(e)})
        return ApiResponse.error(str(e), 400)

    except Exception as e:
        logger.error(
            "Unexpected error in get_reactions", extra={"error": str(e)}, exc_info=e
        )
        return ApiResponse.error("An unexpected error occurred", 500)


@reactions_bp.route("/posts/<int:post_id>", methods=["GET"])
def get_post_reactions(post_id: int):
    """Get reactions for a single post (GET /api/v1/reactions/posts/123?user_id=456)."""
    try:
        # Parse user_id (optional)
        user_id = None
        user_id_param = request.args.get("user_id")
        if user_id_param:
            try:
                user_id = int(user_id_param)
            except ValueError:
                return ApiResponse.error("user_id must be an integer", 400)

        # Process request
        with get_db_session() as session:
            repo = ReactionsRepo(session)
            service = ReactionsService(repo)
            post_reactions = service.get_post_reactions(post_id, user_id)

        # Convert to API response format
        response_data = {
            "post_id": post_reactions.post_id,
            "total_reactions": post_reactions.total_reactions,
            "reaction_counts": [
                {"reaction_type": rc.reaction_type, "count": rc.count}
                for rc in post_reactions.reaction_counts
            ],
            "user_reaction": post_reactions.user_reaction,
        }

        return ApiResponse.success(response_data)

    except Exception as e:
        logger.error(
            "Unexpected error in get_post_reactions",
            extra={"error": str(e), "post_id": post_id},
            exc_info=e,
        )
        return ApiResponse.error("An unexpected error occurred", 500)


@reactions_bp.route("/types", methods=["GET"])
def get_valid_reactions():
    """Get list of valid reaction types (GET /api/v1/reactions/types)."""
    try:
        with get_db_session() as session:
            repo = ReactionsRepo(session)
            service = ReactionsService(repo)
            valid_reactions = service.get_valid_reactions()

        return ApiResponse.success({"valid_reactions": valid_reactions})

    except Exception as e:
        logger.error("Unexpected error in get_valid_reactions", extra={"error": str(e)}, exc_info=e)
        return ApiResponse.error("An unexpected error occurred", 500)


@reactions_bp.route("/stats", methods=["GET"])
def get_reaction_statistics():
    """Get overall reaction statistics (GET /api/v1/reactions/stats)."""
    try:
        with get_db_session() as session:
            repo = ReactionsRepo(session)
            service = ReactionsService(repo)
            stats = service.get_reaction_statistics()

        return ApiResponse.success({"reaction_stats": stats})

    except Exception as e:
        logger.error("Unexpected error in get_reaction_statistics", extra={"error": str(e)}, exc_info=e)
        return ApiResponse.error("An unexpected error occurred", 500)


@reactions_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_auth
def delete_user_reactions(user_id: int):
    """Delete all reactions for a user (DELETE /api/v1/reactions/users/123) - GDPR compliance."""
    current_user_id = request.current_user.id

    # Only allow users to delete their own reactions (or admin in future)
    if current_user_id != user_id:
        return ApiResponse.error("You can only delete your own reactions", 403)

    try:
        with get_db_session() as session:
            repo = ReactionsRepo(session)
            service = ReactionsService(repo)
            deleted_count = service.delete_user_data(user_id)

        return ApiResponse.success(
            {"deleted_count": deleted_count, "message": f"Deleted {deleted_count} reactions"}
        )

    except Exception as e:
        logger.error(
            "Unexpected error in delete_user_reactions",
            extra={"error": str(e), "user_id": user_id, "current_user_id": current_user_id},
            exc_info=e,
        )
        return ApiResponse.error("An unexpected error occurred", 500)