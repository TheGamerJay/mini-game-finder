"""HTTP response helpers for consistent API responses."""
import logging
from typing import Any, Dict, Optional, Tuple

from flask import jsonify
from flask.wrappers import Response

from app.common.errors import AppError

logger = logging.getLogger(__name__)


class ApiResponse:
    """Structured API response helper class."""

    @staticmethod
    def success(data: Any = None, status: int = 200) -> Tuple[Response, int]:
        """Return a successful API response."""
        response_data = {
            "success": True,
            "data": data
        }
        response = jsonify(response_data)
        response.headers["Cache-Control"] = "no-store"
        return response, status

    @staticmethod
    def error(message: str, status: int = 400, details: Optional[Dict[str, Any]] = None) -> Tuple[Response, int]:
        """Return an error API response."""
        response_data = {
            "success": False,
            "error": message
        }
        if details:
            response_data["details"] = details

        response = jsonify(response_data)
        response.headers["Cache-Control"] = "no-store"
        return response, status


def ok(data: Optional[Dict[str, Any]] = None, status: int = 200) -> Tuple[Response, int]:
    """
    Return a successful JSON response.

    Args:
        data: Response data (defaults to empty dict)
        status: HTTP status code (defaults to 200)

    Returns:
        Flask response tuple with JSON data and status code
    """
    response_data = data or {}
    response = jsonify(response_data)
    response.headers["Cache-Control"] = "no-store"
    return response, status


def created(data: Optional[Dict[str, Any]] = None) -> Tuple[Response, int]:
    """Return a 201 Created response."""
    return ok(data, status=201)


def no_content() -> Tuple[Response, int]:
    """Return a 204 No Content response."""
    return ok(status=204)


def handle_error(e: Exception) -> Tuple[Response, int]:
    """
    Global error handler for consistent error responses.

    Args:
        e: The exception that was raised

    Returns:
        Flask response tuple with error data and appropriate status code
    """
    if isinstance(e, AppError):
        # Known application error - return structured response
        logger.info(
            "Application error occurred",
            extra={
                "error_code": e.code,
                "error_message": e.message,
                "error_details": e.details,
                "status_code": e.status,
            },
        )
        return ok(e.to_dict(), status=e.status)

    # Unknown error - log details but return generic response
    logger.exception("Unexpected error occurred", exc_info=e)

    error_response = {
        "error": "internal_error",
        "message": "Something went wrong. Please try again later.",
    }
    return ok(error_response, status=500)


def validate_json_request(required_fields: Optional[list] = None) -> Dict[str, Any]:
    """
    Validate JSON request body and return parsed data.

    Args:
        required_fields: List of required field names

    Returns:
        Parsed JSON data

    Raises:
        ValidationError: If validation fails
    """
    from flask import request
    from app.common.errors import ValidationError

    if not request.is_json:
        raise ValidationError("Request must be JSON")

    try:
        data = request.get_json(force=True)
    except Exception:
        raise ValidationError("Invalid JSON in request body")

    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")

    # Check required fields
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}",
                details={"missing_fields": missing_fields},
            )

    return data