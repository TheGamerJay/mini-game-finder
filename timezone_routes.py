"""
User timezone management routes
Allows users to set their timezone for personalized daily limit resets
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User
from timezone_utils import validate_and_normalize_timezone, get_time_until_user_midnight, TIMEZONE_ALIASES
import logging

logger = logging.getLogger(__name__)

timezone_bp = Blueprint('timezone', __name__)

@timezone_bp.route('/settings/timezone', methods=['GET'])
@login_required
def timezone_settings():
    """Display timezone settings page"""
    return render_template('timezone_settings.html',
                         current_timezone=current_user.user_tz,
                         timezone_aliases=TIMEZONE_ALIASES)

@timezone_bp.route('/api/user/timezone', methods=['POST'])
@login_required
def update_timezone():
    """Update user's timezone setting"""
    try:
        data = request.get_json()
        if not data or 'timezone' not in data:
            return jsonify({'error': 'Timezone is required'}), 400

        timezone_input = data['timezone'].strip()

        # Allow clearing timezone (set to None for UTC default)
        if not timezone_input or timezone_input.lower() in ['', 'utc', 'none', 'clear']:
            current_user.user_tz = None
            db.session.commit()
            logger.info(f"User {current_user.id} cleared timezone setting")
            return jsonify({
                'success': True,
                'message': 'Timezone cleared. Daily limits will reset at midnight UTC.',
                'timezone': None
            })

        # Validate and normalize timezone
        validated_timezone = validate_and_normalize_timezone(timezone_input)
        if not validated_timezone:
            return jsonify({
                'error': f'Invalid timezone: "{timezone_input}". Please use a valid IANA timezone identifier or common alias.',
                'suggestions': list(TIMEZONE_ALIASES.keys())[:10]  # Show first 10 aliases as suggestions
            }), 400

        # Update user's timezone
        current_user.user_tz = validated_timezone
        db.session.commit()

        # Calculate next reset time for confirmation
        try:
            seconds_until_reset, time_str = get_time_until_user_midnight(validated_timezone)
            reset_message = f"Daily limits will now reset at midnight in your timezone. Next reset in {time_str}."
        except Exception:
            reset_message = "Daily limits will now reset at midnight in your timezone."

        logger.info(f"User {current_user.id} updated timezone to {validated_timezone}")
        return jsonify({
            'success': True,
            'message': reset_message,
            'timezone': validated_timezone
        })

    except Exception as e:
        logger.error(f"Error updating timezone for user {current_user.id}: {e}")
        return jsonify({'error': 'Failed to update timezone. Please try again.'}), 500

@timezone_bp.route('/api/user/timezone', methods=['GET'])
@login_required
def get_timezone():
    """Get user's current timezone setting"""
    try:
        user_timezone = current_user.user_tz

        # Calculate time until next reset
        try:
            seconds_until_reset, time_str = get_time_until_user_midnight(user_timezone)
            next_reset_info = {
                'seconds': seconds_until_reset,
                'formatted': time_str
            }
        except Exception:
            next_reset_info = None

        return jsonify({
            'timezone': user_timezone,
            'next_reset': next_reset_info
        })

    except Exception as e:
        logger.error(f"Error getting timezone for user {current_user.id}: {e}")
        return jsonify({'error': 'Failed to get timezone information'}), 500

@timezone_bp.route('/api/timezones/search', methods=['GET'])
def search_timezones():
    """Search for valid timezones based on user input"""
    query = request.args.get('q', '').strip().lower()
    if not query or len(query) < 2:
        return jsonify({'results': []})

    try:
        import pytz

        results = []

        # Search aliases first
        for alias, iana_name in TIMEZONE_ALIASES.items():
            if query in alias:
                results.append({
                    'value': iana_name,
                    'label': f"{alias.title()} ({iana_name})",
                    'type': 'alias'
                })

        # Search IANA timezone names
        for tz_name in sorted(pytz.all_timezones):
            if query in tz_name.lower() and len(results) < 20:
                # Skip if already added via alias
                if not any(r['value'] == tz_name for r in results):
                    # Format nicely
                    display_name = tz_name.replace('_', ' ').replace('/', ' / ')
                    results.append({
                        'value': tz_name,
                        'label': display_name,
                        'type': 'iana'
                    })

        return jsonify({'results': results[:15]})  # Limit to 15 results

    except Exception as e:
        logger.error(f"Error searching timezones: {e}")
        return jsonify({'results': []})

@timezone_bp.route('/api/timezone/detect', methods=['POST'])
@login_required
def detect_timezone():
    """Detect and set timezone from client-side JavaScript"""
    try:
        data = request.get_json()
        if not data or 'timezone' not in data:
            return jsonify({'error': 'Timezone detection data required'}), 400

        detected_timezone = data['timezone']

        # Validate the detected timezone
        validated_timezone = validate_and_normalize_timezone(detected_timezone)
        if not validated_timezone:
            logger.warning(f"Invalid detected timezone: {detected_timezone}")
            return jsonify({'error': 'Could not validate detected timezone'}), 400

        # Only update if user doesn't already have a timezone set
        if not current_user.user_tz:
            current_user.user_tz = validated_timezone
            db.session.commit()
            logger.info(f"Auto-detected and set timezone {validated_timezone} for user {current_user.id}")

            return jsonify({
                'success': True,
                'message': f'Timezone automatically detected as {validated_timezone}',
                'timezone': validated_timezone
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Timezone already set',
                'timezone': current_user.user_tz
            })

    except Exception as e:
        logger.error(f"Error detecting timezone for user {current_user.id}: {e}")
        return jsonify({'error': 'Timezone detection failed'}), 500