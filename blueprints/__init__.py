# 🐍 Block B — Flask blueprints package
# Import all blueprints for easy registration

from .credits import credits_bp
from .game import game_bp
from .prefs import prefs_bp

__all__ = ['credits_bp', 'game_bp', 'prefs_bp']