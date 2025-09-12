# api_routes.py
"""API routes for Mini Word Finder."""
from flask import Blueprint, request, jsonify, current_app
from image_utils import save_to_storage

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/upload-image', methods=['POST'])
def upload_image():
    """
    Upload an image file.
    Returns: {"url": "..."} or {"error": "..."}
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
        
    f = request.files['file']
    if not f:
        return jsonify({"error": "Empty file"}), 400
        
    try:
        url = save_to_storage(
            f,
            storage_backend=current_app.config.get("STORAGE_BACKEND", "local"),
            config=current_app.config
        )
        return jsonify({"url": url})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
