import os
import random

ASSISTANT_NAME = os.getenv("HINT_ASSISTANT_NAME", "Word Cipher")

def rephrase_hint_or_fallback(word: str, row: int, col: int, dir_word: str, arrow: str, length: int) -> str:
    """Generate helpful hints without OpenAI dependency"""

    # Convert row/col to 1-based for user display
    display_row = row + 1
    display_col = col + 1

    # Create varied hint templates
    templates = [
        f"Look at row {display_row}, column {display_col}, then go {dir_word} {arrow} for {length} letters.",
        f"Find '{word}' starting from row {display_row}, column {display_col}, moving {dir_word}.",
        f"The word '{word}' begins at position ({display_row}, {display_col}) and goes {dir_word}.",
        f"Start at row {display_row}, column {display_col} and trace {dir_word} to find '{word}'.",
        f"Look for '{word}' - it starts at row {display_row}, column {display_col}, going {dir_word}."
    ]

    # Add word-specific hints
    if len(word) >= 4:
        first_letters = word[:2].upper()
        templates.append(f"Search for a word starting with '{first_letters}' at row {display_row}, column {display_col}.")

    if word.upper() in ['CAT', 'DOG', 'BIRD', 'FISH']:
        templates.append(f"Find the animal '{word}' starting at row {display_row}, column {display_col}.")

    return random.choice(templates)