# puzzles.py
"""
Word-search puzzle generator for Mini Word Finder.

API:
    grid, words = make_puzzle(rows, cols, words_count, seed=None, dictionary=None)

- grid: list[list[str]] of uppercase letters
- words: list[str] of the words that were successfully embedded (uppercase)
"""

from __future__ import annotations
import random
import string
from typing import List, Tuple, Optional

# 8 directions: E, S, W, N, SE, NW, SW, NE
DIRECTIONS: List[tuple[int, int]] = [
    (0, 1), (1, 0), (0, -1), (-1, 0),
    (1, 1), (-1, -1), (1, -1), (-1, 1),
]

# Default small dictionary (all caps). Replace/extend as you like.
DEFAULT_DICTIONARY: List[str] = [
    "CODE","DEBUG","BUILD","GRID","ARRAY","CLASS","LOGIC","STACK","QUEUE","LOOP",
    "PYTHON","FLASK","ROUTE","LOGIN","TOKEN","RESET","EMAIL","SCORE","WORDS",
    "ROBOT","LASER","CLOUD","VALUE","INDEX","FIELD","MODEL","QUERY","SEARCH",
    "LETTER","PUZZLE","RANDOM","BOARD","CLICK","TIMER","EASY","MEDIUM","HARD"
]

def _fits(grid: List[List[Optional[str]]], x: int, y: int, dx: int, dy: int, word: str) -> bool:
    rows, cols = len(grid), len(grid[0])
    # end cell
    ex = x + dx * (len(word) - 1)
    ey = y + dy * (len(word) - 1)
    if not (0 <= ex < cols and 0 <= ey < rows):
        return False
    # collision check / overlap compatibility
    cx, cy = x, y
    for ch in word:
        cell = grid[cy][cx]
        if cell is not None and cell != ch:
            return False
        cx += dx; cy += dy
    return True

def _place(grid: List[List[Optional[str]]], x: int, y: int, dx: int, dy: int, word: str) -> None:
    cx, cy = x, y
    for ch in word:
        grid[cy][cx] = ch
        cx += dx; cy += dy

def make_puzzle(
    rows: int,
    cols: int,
    words_count: int,
    seed: Optional[int] = None,
    dictionary: Optional[List[str]] = None
) -> Tuple[List[List[str]], List[str]]:
    """
    Generate a word-search puzzle.
    - Only words that actually get embedded are returned in `placed_words`.
    - If not enough words can be placed after reasonable attempts, it returns as many as fit.
    """
    rng = random.Random(seed)

    # Prepare dictionary: uppercase and filter lengths to fit board.
    dict_src = dictionary or DEFAULT_DICTIONARY
    pool = sorted({w.strip().upper() for w in dict_src if 3 <= len(w) <= max(1, min(rows, cols))})
    if not pool:
        raise ValueError("Dictionary has no words that fit this board.")

    # Choose candidate words (oversample a bit to increase placement success)
    candidates = rng.sample(pool, k=min(max(words_count * 2, words_count), len(pool)))

    # Empty grid of None
    grid: List[List[Optional[str]]] = [[None for _ in range(cols)] for _ in range(rows)]
    placed_words: List[str] = []

    # Try to place until we have words_count or exhaust candidates
    for word in candidates:
        if len(placed_words) >= words_count:
            break

        # Randomize direction & starts each attempt
        success = False
        attempts = 0
        while attempts < 300 and not success:
            attempts += 1
            dx, dy = rng.choice(DIRECTIONS)
            x = rng.randrange(cols)
            y = rng.randrange(rows)

            if _fits(grid, x, y, dx, dy, word):
                _place(grid, x, y, dx, dy, word)
                placed_words.append(word)
                success = True

    # If we still don't have enough words, try shorter words quickly
    if len(placed_words) < words_count:
        remaining = [w for w in pool if w not in placed_words]
        remaining.sort(key=len)  # shortest first
        for word in remaining:
            if len(placed_words) >= words_count:
                break
            success = False
            attempts = 0
            while attempts < 200 and not success:
                attempts += 1
                dx, dy = rng.choice(DIRECTIONS)
                x = rng.randrange(cols)
                y = rng.randrange(rows)
                if _fits(grid, x, y, dx, dy, word):
                    _place(grid, x, y, dx, dy, word)
                    placed_words.append(word)
                    success = True

    # Fill blanks with random letters
    letters = string.ascii_uppercase
    final_grid: List[List[str]] = []
    for r in range(rows):
        row_out: List[str] = []
        for c in range(cols):
            ch = grid[r][c]
            row_out.append(ch if ch is not None else rng.choice(letters))
        final_grid.append(row_out)

    return final_grid, placed_words


# --- quick self-test (optional) ---
if __name__ == "__main__":
    g, w = make_puzzle(10, 10, 6, seed=123)
    print("\n".join(" ".join(r) for r in g))
    print("WORDS:", w)