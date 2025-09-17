# 🐍 Block B — Flask blueprints: User Preferences API
# This blueprint handles user preferences like auto-teach and mute settings

from flask import Blueprint, request, jsonify, abort, current_app
from csrf_utils import require_csrf
from blueprints.credits import _get_db_connection, _get_user_id
import psycopg2
from psycopg2.extras import RealDictCursor

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

@prefs_bp.route("/get", methods=["GET"])
def get_prefs():
    """Get user preferences (all or specific key)"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    key = request.args.get('key')  # Optional: get specific preference

    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if key:
                    # Get specific preference
                    if key not in VALID_PREFS:
                        return jsonify({"error": f"Invalid preference key: {key}"}), 400

                    cur.execute("""
                        SELECT value FROM user_prefs
                        WHERE user_id = %s AND key = %s
                    """, (user_id, key))

                    row = cur.fetchone()
                    value = row["value"] if row else VALID_PREFS[key]

                    return jsonify({
                        "ok": True,
                        "key": key,
                        "value": value,
                        "is_default": row is None
                    })
                else:
                    # Get all preferences
                    cur.execute("""
                        SELECT key, value FROM user_prefs
                        WHERE user_id = %s
                    """, (user_id,))

                    user_prefs = {row["key"]: row["value"] for row in cur.fetchall()}

                    # Merge with defaults for any missing keys
                    all_prefs = {}
                    for pref_key, default_value in VALID_PREFS.items():
                        all_prefs[pref_key] = user_prefs.get(pref_key, default_value)

                    return jsonify({
                        "ok": True,
                        "preferences": all_prefs,
                        "defaults": VALID_PREFS
                    })

    except Exception as e:
        current_app.logger.error(f"Error getting preferences for user {user_id}: {e}")
        return jsonify({"error": "Failed to get preferences"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@prefs_bp.route("/set", methods=["POST"])
@require_csrf
def set_pref():
    """Set a user preference"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json(force=True) or {}
    key = data.get("key")
    value = data.get("value")

    if not key:
        return jsonify({"error": "Missing 'key' parameter"}), 400

    if value is None:
        return jsonify({"error": "Missing 'value' parameter"}), 400

    # Validate preference key
    if key not in VALID_PREFS:
        return jsonify({"error": f"Invalid preference key: {key}"}), 400

    # Convert value to string for storage
    value_str = str(value).lower() if isinstance(value, bool) else str(value)

    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Insert or update preference
                cur.execute("""
                    INSERT INTO user_prefs (user_id, key, value, created_at, updated_at)
                    VALUES (%s, %s, %s, now(), now())
                    ON CONFLICT (user_id, key)
                    DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                """, (user_id, key, value_str))

        current_app.logger.info(f"User {user_id} set preference {key} = {value_str}")

        return jsonify({
            "ok": True,
            "key": key,
            "value": value_str,
            "message": f"Preference '{key}' updated successfully"
        })

    except Exception as e:
        current_app.logger.error(f"Error setting preference for user {user_id}: {e}")
        return jsonify({"error": "Failed to set preference"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@prefs_bp.route("/set-multiple", methods=["POST"])
@require_csrf
def set_multiple_prefs():
    """Set multiple preferences at once"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json(force=True) or {}
    preferences = data.get("preferences", {})

    if not isinstance(preferences, dict):
        return jsonify({"error": "preferences must be an object"}), 400

    # Validate all keys first
    invalid_keys = [key for key in preferences.keys() if key not in VALID_PREFS]
    if invalid_keys:
        return jsonify({"error": f"Invalid preference keys: {invalid_keys}"}), 400

    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                updated_prefs = {}

                for key, value in preferences.items():
                    value_str = str(value).lower() if isinstance(value, bool) else str(value)

                    cur.execute("""
                        INSERT INTO user_prefs (user_id, key, value, created_at, updated_at)
                        VALUES (%s, %s, %s, now(), now())
                        ON CONFLICT (user_id, key)
                        DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                    """, (user_id, key, value_str))

                    updated_prefs[key] = value_str

        current_app.logger.info(f"User {user_id} updated {len(updated_prefs)} preferences")

        return jsonify({
            "ok": True,
            "updated": updated_prefs,
            "count": len(updated_prefs),
            "message": f"Updated {len(updated_prefs)} preferences successfully"
        })

    except Exception as e:
        current_app.logger.error(f"Error setting multiple preferences for user {user_id}: {e}")
        return jsonify({"error": "Failed to set preferences"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@prefs_bp.route("/reset", methods=["POST"])
@require_csrf
def reset_prefs():
    """Reset preferences to defaults (delete custom values)"""
    user_id = _get_user_id()
    if not user_id:
        return jsonify({"error": "Please log in"}), 401

    data = request.get_json(force=True) or {}
    keys = data.get("keys")  # Optional: reset specific keys, or all if None

    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if keys:
                    # Reset specific keys
                    if not isinstance(keys, list):
                        return jsonify({"error": "keys must be an array"}), 400

                    invalid_keys = [key for key in keys if key not in VALID_PREFS]
                    if invalid_keys:
                        return jsonify({"error": f"Invalid preference keys: {invalid_keys}"}), 400

                    cur.execute("""
                        DELETE FROM user_prefs
                        WHERE user_id = %s AND key = ANY(%s)
                    """, (user_id, keys))

                    reset_count = cur.rowcount
                    message = f"Reset {reset_count} preferences to defaults"
                else:
                    # Reset all preferences
                    cur.execute("""
                        DELETE FROM user_prefs WHERE user_id = %s
                    """, (user_id,))

                    reset_count = cur.rowcount
                    message = f"Reset all {reset_count} preferences to defaults"
                    keys = list(VALID_PREFS.keys())

        current_app.logger.info(f"User {user_id} reset {reset_count} preferences")

        return jsonify({
            "ok": True,
            "reset_keys": keys,
            "reset_count": reset_count,
            "defaults": {key: VALID_PREFS[key] for key in (keys or VALID_PREFS.keys())},
            "message": message
        })

    except Exception as e:
        current_app.logger.error(f"Error resetting preferences for user {user_id}: {e}")
        return jsonify({"error": "Failed to reset preferences"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@prefs_bp.route("/schema", methods=["GET"])
def get_prefs_schema():
    """Get the preferences schema (valid keys and defaults)"""
    return jsonify({
        "ok": True,
        "schema": VALID_PREFS,
        "description": {
            "auto_teach_no_timer": "Enable auto-teach in no-timer game mode",
            "auto_teach_timer": "Enable auto-teach in timer game mode",
            "speak_enabled": "Enable text-to-speech pronunciation",
            "lesson_auto_close": "Automatically close lesson overlays",
            "reveal_confirmation": "Ask for confirmation before revealing words",
            "game_sound_effects": "Enable sound effects during gameplay",
            "theme": "UI theme preference (default, dark, light)",
            "language": "Language preference for lessons and UI"
        }
    })