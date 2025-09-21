"""Custom exception hierarchy for clean error handling."""
from typing import Any, Dict, Optional


class AppError(Exception):
    """Base application error with structured error responses."""

    status: int = 400
    code: str = "app_error"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON response."""
        result = {
            "error": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(AppError):
    """Request validation failed."""

    status = 400
    code = "validation_error"


class NotFound(AppError):
    """Requested resource not found."""

    status = 404
    code = "not_found"


class AlreadyReacted(AppError):
    """User has already reacted to this post."""

    status = 200  # Not an error from user perspective
    code = "already_reacted"


class Unauthorized(AppError):
    """User is not authenticated."""

    status = 401
    code = "unauthorized"


class Forbidden(AppError):
    """User lacks permission for this action."""

    status = 403
    code = "forbidden"


class RateLimited(AppError):
    """User has exceeded rate limits."""

    status = 429
    code = "rate_limited"


class DatabaseError(AppError):
    """Database operation failed."""

    status = 500
    code = "database_error"


class IntegrityConstraintViolation(DatabaseError):
    """Database integrity constraint was violated."""

    status = 409
    code = "integrity_violation"