"""
Public route decorator utility
"""

def public(view):
    """Mark a view as public (no authentication required)"""
    view._public = True
    return view