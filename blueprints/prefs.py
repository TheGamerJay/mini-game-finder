# 🐍 Block B — Flask blueprints: User Preferences API
# This blueprint handles user preferences like auto-teach and mute settings

from flask import Blueprint, request, jsonify, abort, current_app
from csrf_utils import require_csrf
from blueprints.credits import _get_user_id
from models import db, User
import json

prefs_bp = Blueprint("prefs", __name__, url_prefix="/api/prefs")

# Valid preference keys and their default values
VALID_PREFS = {
    "auto_teach_no_timer": "true",      # Auto-teach in no-timer mode
    "auto_teach_timer": "false",        # Auto-teach in timer mode
    "speak_enabled": "true",            # Text-to-speech enabled
    "lesson_auto_close": "false",       # Auto-close lesson overlay
    "reveal_confirmation": "true",      # Confirm before revealing words
    "game_sound_effects": "true",       # Sound effects in game
    "theme": "default",                 # UI theme preference
    "language": "en",                   # Language preference
}

def _get_user_prefs(user):
    """Get user preferences as a dict"""
    if not user.user_preferences:
        return VALID_PREFS.copy()

    try:
        stored_prefs = json.loads(user.user_preferences)
        # Merge with defaults for any missing keys
        prefs = VALID_PREFS.copy()
        prefs.update(stored_prefs)
        return prefs
    except (json.JSONDecodeError, TypeError):
        current_app.logger.warning(f"Invalid JSON in user preferences for user {user.id}")
        return VALID_PREFS.copy()

def _save_user_prefs(user, prefs):
    """Save user preferences as JSON"""
    try:
        user.user_preferences = json.dumps(prefs)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to save preferences for user {user.id}: {e}")
        return False

@prefs_bp.route("/get", methods=["GET"])
def get_prefs():
    """Get user preferences (all or specific key)"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    key = request.args.get('key')  # Optional: get specific preference

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        prefs = _get_user_prefs(user)

        if key:
            # Get specific preference
            if key not in VALID_PREFS:
                return jsonify({"error": f"Invalid preference key: {key}"}), 400

            return jsonify({
                "ok": True,
                "key": key,
                "value": prefs.get(key, VALID_PREFS[key])
            })
        else:
            # Get all preferences
            return jsonify({
                "ok": True,
                "preferences": prefs
            })

    except Exception as e:
        current_app.logger.error(f"Error getting preferences for user {user_id}: {e}")
        return jsonify({"error": "Failed to get preferences"}), 500

@prefs_bp.route("/set", methods=["POST"])
@require_csrf
def set_pref():
    """Set a single preference"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json() or {}
    key = data.get("key")
    value = data.get("value")

    if not key or value is None:
        return jsonify({"error": "key and value required"}), 400

    if key not in VALID_PREFS:
        return jsonify({"error": f"Invalid preference key: {key}"}), 400

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        prefs = _get_user_prefs(user)
        prefs[key] = str(value)

        if _save_user_prefs(user, prefs):
            return jsonify({
                "ok": True,
                "key": key,
                "value": prefs[key]
            })
        else:
            return jsonify({"error": "Failed to save preference"}), 500

    except Exception as e:
        current_app.logger.error(f"Error setting preference for user {user_id}: {e}")
        return jsonify({"error": "Failed to set preference"}), 500

@prefs_bp.route("/set-multiple", methods=["POST"])
@require_csrf
def set_multiple_prefs():
    """Set multiple preferences at once"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json() or {}
    new_prefs = data.get("preferences", {})

    if not isinstance(new_prefs, dict):
        return jsonify({"error": "preferences must be an object"}), 400

    # Validate all keys first
    invalid_keys = [k for k in new_prefs.keys() if k not in VALID_PREFS]
    if invalid_keys:
        return jsonify({"error": f"Invalid preference keys: {invalid_keys}"}), 400

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        prefs = _get_user_prefs(user)

        # Update with new preferences
        for key, value in new_prefs.items():
            prefs[key] = str(value)

        if _save_user_prefs(user, prefs):
            return jsonify({
                "ok": True,
                "updated": list(new_prefs.keys()),
                "preferences": prefs
            })
        else:
            return jsonify({"error": "Failed to save preferences"}), 500

    except Exception as e:
        current_app.logger.error(f"Error setting multiple preferences for user {user_id}: {e}")
        return jsonify({"error": "Failed to set preferences"}), 500

@prefs_bp.route("/prefs/reset", methods=["POST"])
@require_csrf
def reset_prefs():
    """Reset preferences to defaults"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        defaults = VALID_PREFS.copy()

        if _save_user_prefs(user, defaults):
            return jsonify({
                "ok": True,
                "message": "Preferences reset to defaults",
                "preferences": defaults
            })
        else:
            return jsonify({"error": "Failed to reset preferences"}), 500

    except Exception as e:
        current_app.logger.error(f"Error resetting preferences for user {user_id}: {e}")
        return jsonify({"error": "Failed to reset preferences"}), 500

@prefs_bp.route("/schema", methods=["GET"])
def get_prefs_schema():
    """Get valid preference keys and their default values"""
    return jsonify({
        "ok": True,
        "valid_preferences": VALID_PREFS,
        "description": {
            "auto_teach_no_timer": "Automatically show word lessons in relaxed mode",
            "auto_teach_timer": "Automatically show word lessons in timed mode",
            "speak_enabled": "Enable text-to-speech pronunciation",
            "lesson_auto_close": "Automatically close lesson overlays after 5 seconds",
            "reveal_confirmation": "Ask for confirmation before revealing words",
            "game_sound_effects": "Enable sound effects during gameplay",
            "theme": "UI theme preference (default, dark, light)",
            "language": "Language preference (en, es, fr, etc.)"
        }
    })