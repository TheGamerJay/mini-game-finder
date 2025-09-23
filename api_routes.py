# api_routes.py
"""API routes for Mini Game Finder."""
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

@bp.route('/word/lesson', methods=['GET'])
def get_word_lesson():
    """Get lesson data for a word (used by auto-teach system)"""
    word = request.args.get('word', '').upper()

    if not word:
        return jsonify({"error": "word parameter required"}), 400

    # Word definitions for lessons
    word_definitions = {
        "BOARD": {"def": "A flat piece of wood, plastic, or other material used for various purposes", "example": "We wrote on the board with chalk."},
        "MOON": {"def": "Earth's natural satellite that orbits around our planet", "example": "The moon shines brightly in the night sky."},
        "SEARCH": {"def": "To look for something carefully", "example": "I will search for my lost keys."},
        "MOUNTAIN": {"def": "A large natural elevation of land rising above the surrounding area", "example": "We climbed the mountain to see the view."},
        "OCEAN": {"def": "A very large body of salt water", "example": "The Pacific Ocean is the largest ocean on Earth."},
        "TREE": {"def": "A woody plant that is typically tall with a trunk and branches", "example": "Birds nest in the old oak tree."},
        "HOUSE": {"def": "A building where people live", "example": "My house has a red door."},
        "WATER": {"def": "A clear liquid that is essential for life", "example": "Please drink more water to stay healthy."},
        "LIGHT": {"def": "Brightness that allows us to see things", "example": "Turn on the light so we can read."},
        "BOOK": {"def": "A set of printed pages bound together", "example": "I'm reading an interesting book about space."},
        "FIRE": {"def": "The process of combustion that produces heat and light", "example": "We warmed our hands by the fire."},
        "RIVER": {"def": "A large stream of water flowing toward the sea", "example": "The river flows through the valley."},
        "CLOUD": {"def": "A visible mass of water droplets in the sky", "example": "The white cloud drifted across the blue sky."},
        "STONE": {"def": "A hard solid mineral matter", "example": "We skipped stones across the lake."},
        "BIRD": {"def": "A warm-blooded animal with feathers and wings", "example": "The bird built a nest in the tree."}
    }

    # Get definition or use generic one
    word_info = word_definitions.get(word, {
        "def": f"A word commonly found in word search puzzles",
        "example": f"The word {word} can be found in many vocabulary lists."
    })

    lesson_data = {
        "word": word,
        "definition": word_info["def"],
        "example": word_info["example"],
        "phonics": word.lower(),
        "difficulty": "medium",
        "category": "general"
    }

    return jsonify({
        "ok": True,
        "lesson": lesson_data
    })
