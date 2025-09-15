"""
War Badges Catalog - Badge themes, icons, and display info
"""

WAR_BADGE_CODE = "war_champion_lvl"

# Level catalog with display themes
CATALOG = [
    # (level, name, icon, theme)
    (1, "War Champion • Bronze",   "shield",   "bronze"),
    (2, "War Champion • Silver",   "laurel",   "silver"),
    (3, "War Champion • Gold",     "crown",    "gold"),
    (4, "War Champion • Platinum", "sword",    "platinum"),
    (5, "War Champion • Diamond",  "phoenix",  "diamond"),
]

def level_theme(level: int) -> dict | None:
    """
    Get display theme for a badge level

    Args:
        level: Badge level (1-5)

    Returns:
        Dict with theme info or None if invalid level
    """
    for lv, name, icon, theme in CATALOG:
        if lv == level:
            return {
                "level": lv,
                "name": name,
                "icon": icon,
                "theme": theme
            }
    return None

def next_threshold(level: int) -> int | None:
    """
    Get wins required for next level

    Args:
        level: Current level

    Returns:
        Wins needed for next level or None if max level
    """
    from services.war_badges import LEVELS

    if level < len(LEVELS):
        return LEVELS[level]  # Index level gives next threshold
    return None

def get_catalog() -> list[dict]:
    """
    Get full catalog for API responses

    Returns:
        List of level dictionaries
    """
    from services.war_badges import LEVELS

    result = []
    for i, (lv, name, icon, theme) in enumerate(CATALOG):
        result.append({
            "level": lv,
            "wins_required": LEVELS[i] if i < len(LEVELS) else 0,
            "name": name,
            "icon": icon,
            "theme": theme
        })
    return result