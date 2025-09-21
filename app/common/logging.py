"""Structured logging configuration for the application."""
import logging
import logging.config
import os
import sys
from typing import Any, Dict


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Determine if we're in production
    is_production = os.getenv("FLASK_ENV") == "production"

    # Base logging configuration
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "%(levelname)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "detailed" if is_production else "simple",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            # Application loggers
            "app": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # Feature-specific loggers
            "app.features.auth": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.features.posts": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.features.reactions": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.features.comments": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.features.payments": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # Third-party loggers (quieter in production)
            "sqlalchemy.engine": {
                "level": "WARNING" if is_production else "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "werkzeug": {
                "level": "WARNING" if is_production else "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }

    # Apply configuration
    logging.config.dictConfig(config)


def get_feature_logger(feature_name: str) -> logging.Logger:
    """
    Get a logger for a specific feature.

    Args:
        feature_name: Name of the feature (e.g., 'reactions', 'posts')

    Returns:
        Configured logger for the feature
    """
    return logging.getLogger(f"app.features.{feature_name}")


def log_api_request(
    feature: str,
    endpoint: str,
    user_id: int,
    method: str = "POST",
    extra_data: Dict[str, Any] = None,
) -> None:
    """
    Log an API request with structured data.

    Args:
        feature: Feature name (e.g., 'reactions')
        endpoint: Endpoint name (e.g., 'create_reaction')
        user_id: ID of the user making the request
        method: HTTP method
        extra_data: Additional data to log
    """
    logger = get_feature_logger(feature)

    log_data = {
        "event": "api_request",
        "feature": feature,
        "endpoint": endpoint,
        "user_id": user_id,
        "method": method,
    }

    if extra_data:
        log_data.update(extra_data)

    logger.info("API request", extra=log_data)


def log_api_response(
    feature: str,
    endpoint: str,
    user_id: int,
    status_code: int,
    success: bool = True,
    extra_data: Dict[str, Any] = None,
) -> None:
    """
    Log an API response with structured data.

    Args:
        feature: Feature name
        endpoint: Endpoint name
        user_id: ID of the user
        status_code: HTTP status code
        success: Whether the request was successful
        extra_data: Additional data to log
    """
    logger = get_feature_logger(feature)

    log_data = {
        "event": "api_response",
        "feature": feature,
        "endpoint": endpoint,
        "user_id": user_id,
        "status_code": status_code,
        "success": success,
    }

    if extra_data:
        log_data.update(extra_data)

    level = logging.INFO if success else logging.WARNING
    logger.log(level, "API response", extra=log_data)