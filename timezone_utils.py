"""
Timezone utilities for user-specific daily limit resets
Based on comprehensive timezone-aware daily limit system requirements
"""

import pytz
from datetime import datetime, timezone
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Common timezone aliases for user convenience
TIMEZONE_ALIASES = {
    'eastern': 'America/New_York',
    'est': 'America/New_York',
    'edt': 'America/New_York',
    'central': 'America/Chicago',
    'cst': 'America/Chicago',
    'cdt': 'America/Chicago',
    'mountain': 'America/Denver',
    'mst': 'America/Denver',
    'mdt': 'America/Denver',
    'pacific': 'America/Los_Angeles',
    'pst': 'America/Los_Angeles',
    'pdt': 'America/Los_Angeles',
    'london': 'Europe/London',
    'paris': 'Europe/Paris',
    'berlin': 'Europe/Berlin',
    'tokyo': 'Asia/Tokyo',
    'sydney': 'Australia/Sydney',
    'mumbai': 'Asia/Kolkata',
    'dubai': 'Asia/Dubai'
}

def validate_and_normalize_timezone(user_input: str) -> Optional[str]:
    """
    Validate and normalize timezone input to IANA timezone identifier

    Args:
        user_input: User-provided timezone string (could be alias, IANA name, etc.)

    Returns:
        Valid IANA timezone identifier or None if invalid
    """
    if not user_input:
        return None

    # Normalize input
    normalized = user_input.strip().lower()

    # Check aliases first
    if normalized in TIMEZONE_ALIASES:
        iana_tz = TIMEZONE_ALIASES[normalized]
        try:
            pytz.timezone(iana_tz)
            return iana_tz
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Invalid alias mapping: {normalized} -> {iana_tz}")
            return None

    # Try original input as IANA timezone
    try:
        pytz.timezone(user_input.strip())
        return user_input.strip()
    except pytz.UnknownTimeZoneError:
        pass

    # Try to match partial timezone names
    user_input_clean = user_input.strip().replace(' ', '_').replace('-', '_')
    for tz_name in pytz.all_timezones:
        if user_input_clean.lower() in tz_name.lower():
            try:
                pytz.timezone(tz_name)
                return tz_name
            except pytz.UnknownTimeZoneError:
                continue

    logger.info(f"Could not validate timezone: {user_input}")
    return None

def get_user_midnight_utc(user_timezone: Optional[str]) -> datetime:
    """
    Calculate when midnight occurs in the user's timezone, returned as UTC datetime

    Args:
        user_timezone: IANA timezone identifier

    Returns:
        UTC datetime representing user's next midnight
    """
    if not user_timezone:
        # Fallback to UTC midnight
        now_utc = datetime.now(timezone.utc)
        next_midnight = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_midnight <= now_utc:
            # If it's already past midnight UTC today, get tomorrow's midnight
            from datetime import timedelta
            next_midnight += timedelta(days=1)
        return next_midnight

    try:
        user_tz = pytz.timezone(user_timezone)

        # Get current time in user's timezone
        now_utc = datetime.now(timezone.utc)
        now_user = now_utc.astimezone(user_tz)

        # Calculate next midnight in user's timezone
        next_midnight_user = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_midnight_user <= now_user:
            # If it's already past midnight today, get tomorrow's midnight
            from datetime import timedelta
            next_midnight_user += timedelta(days=1)

        # Convert back to UTC
        next_midnight_utc = next_midnight_user.astimezone(timezone.utc)
        return next_midnight_utc.replace(tzinfo=None)  # Return as naive datetime for SQLAlchemy

    except (pytz.UnknownTimeZoneError, Exception) as e:
        logger.warning(f"Error calculating midnight for timezone {user_timezone}: {e}")
        # Fallback to UTC midnight
        now_utc = datetime.now(timezone.utc)
        next_midnight = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_midnight <= now_utc:
            from datetime import timedelta
            next_midnight += timedelta(days=1)
        return next_midnight.replace(tzinfo=None)

def get_time_until_user_midnight(user_timezone: Optional[str]) -> Tuple[int, str]:
    """
    Get time remaining until user's midnight and formatted string

    Args:
        user_timezone: IANA timezone identifier

    Returns:
        Tuple of (seconds_until_midnight, formatted_time_string)
    """
    try:
        next_midnight_utc = get_user_midnight_utc(user_timezone)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        time_diff = next_midnight_utc - now_utc
        seconds_remaining = int(time_diff.total_seconds())

        if seconds_remaining <= 0:
            return 0, "now"

        hours = seconds_remaining // 3600
        minutes = (seconds_remaining % 3600) // 60

        if hours > 0:
            if minutes > 0:
                return seconds_remaining, f"{hours}h {minutes}m"
            else:
                return seconds_remaining, f"{hours}h"
        elif minutes > 0:
            return seconds_remaining, f"{minutes}m"
        else:
            return seconds_remaining, "< 1m"

    except Exception as e:
        logger.warning(f"Error calculating time until midnight: {e}")
        return 86400, "24h"  # Fallback to 24 hours

def detect_timezone_from_request(request) -> Optional[str]:
    """
    Attempt to detect user timezone from browser/request headers

    Args:
        request: Flask request object

    Returns:
        Detected IANA timezone identifier or None
    """
    # This would typically use JavaScript on the client side to detect timezone
    # and send it in a header or form data. For now, return None to use UTC fallback.

    # Example implementation if timezone is sent via header:
    # detected_tz = request.headers.get('X-User-Timezone')
    # if detected_tz:
    #     return validate_and_normalize_timezone(detected_tz)

    return None

def format_time_in_user_timezone(utc_datetime: datetime, user_timezone: Optional[str]) -> str:
    """
    Format a UTC datetime in the user's timezone

    Args:
        utc_datetime: UTC datetime to format
        user_timezone: IANA timezone identifier

    Returns:
        Formatted time string in user's timezone
    """
    if not user_timezone:
        return utc_datetime.strftime('%I:%M %p UTC')

    try:
        user_tz = pytz.timezone(user_timezone)

        # Convert UTC to timezone-aware UTC, then to user timezone
        if utc_datetime.tzinfo is None:
            utc_aware = utc_datetime.replace(tzinfo=timezone.utc)
        else:
            utc_aware = utc_datetime

        user_time = utc_aware.astimezone(user_tz)
        return user_time.strftime('%I:%M %p')

    except Exception as e:
        logger.warning(f"Error formatting time for timezone {user_timezone}: {e}")
        return utc_datetime.strftime('%I:%M %p UTC')