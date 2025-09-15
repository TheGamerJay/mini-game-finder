"""
War Badges Service - Manage leveled war champion badges
"""
from models import db, User, UserBadge

BADGE_CODE = "war_champion_lvl"
LEVELS = [1, 3, 10, 25, 50]  # wins needed for Lv1..Lv5

def _wins_to_level(wins: int) -> int:
    """Calculate badge level from total wins"""
    lvl = 0
    for need in LEVELS:
        if wins >= need:
            lvl += 1
    return lvl

def record_war_win(user_id: int):
    """
    Increment user's war_wins and upsert leveled badge

    Args:
        user_id: User ID of the war winner
    """
    user = User.query.get(user_id)
    if not user:
        return

    # Increment war wins
    user.war_wins = (user.war_wins or 0) + 1
    new_level = _wins_to_level(user.war_wins)

    # Update or create badge
    ub = UserBadge.query.filter_by(user_id=user_id, code=BADGE_CODE).first()

    if new_level > 0:
        if not ub:
            # Create new badge
            ub = UserBadge(user_id=user_id, code=BADGE_CODE, level=new_level)
            db.session.add(ub)
        else:
            # Update existing badge level if changed
            if ub.level != new_level:
                ub.level = new_level

    db.session.commit()

def get_user_badge(user_id: int) -> dict | None:
    """
    Get user's war champion badge info

    Returns:
        Dict with badge info or None if no badge
    """
    user = User.query.get(user_id)
    if not user:
        return None

    ub = UserBadge.query.filter_by(user_id=user_id, code=BADGE_CODE).first()

    if not ub:
        return None

    from services.war_badges_catalog import level_theme
    theme = level_theme(ub.level)

    return {
        "has_badge": True,
        "level": ub.level,
        "wins": user.war_wins or 0,
        "name": theme["name"] if theme else f"War Champion Lv{ub.level}",
        "icon": theme["icon"] if theme else "trophy",
        "theme": theme["theme"] if theme else "gold"
    }