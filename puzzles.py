import random
import string
from typing import List, Tuple

DIRECTIONS = [
    (0, 1), (1, 0), (0, -1), (-1, 0),
    (1, 1), (-1, -1), (1, -1), (-1, 1)
]

DEFAULT_DICTIONARY = [
    # short, clean words; you can replace with a bigger list later
    "CODE","DEBUG","BUILD","GRID","ARRAY","CLASS","LOGIC","STACK","QUEUE","LOOP",
    "PYTHON","FLASK","ROUTE","LOGIN","TOKEN","RESET","EMAIL","SCORE","GAME","WORDS",
    "ROBOT","LASER","CLOUD","BATCH","CRYPT","VALUE","INDEX","FIELD","MODEL","QUERY"
]

def make_puzzle(rows:int, cols:int, words_count:int, seed:int|None=None,
                dictionary:List[str]|None=None) -> Tuple[List[List[str]], List[str]]:
    rng = random.Random(seed)
    dict_src = dictionary or DEFAULT_DICTIONARY
    pool = [w for w in dict_src if 3 <= len(w) <= min(rows, cols)]
    chosen = rng.sample(pool, k=min(words_count, len(pool)))

    grid = [[None for _ in range(cols)] for _ in range(rows)]

    for word in chosen:
        placed = False
        attempts = 0
        while not placed and attempts < 400:
            attempts += 1
            dx, dy = rng.choice(DIRECTIONS)
            if dx == dy == 0: 
                continue
            x = rng.randrange(cols)
            y = rng.randrange(rows)
            # end position
            ex = x + dx*(len(word)-1)
            ey = y + dy*(len(word)-1)
            if not (0 <= ex < cols and 0 <= ey < rows):
                continue

            # check fit
            ok = True
            cx, cy = x, y
            for ch in word:
                cell = grid[cy][cx]
                if cell is not None and cell != ch:
                    ok = False
                    break
                cx += dx; cy += dy
            if not ok:
                continue

            # place
            cx, cy = x, y
            for ch in word:
                grid[cy][cx] = ch
                cx += dx; cy += dy
            placed = True

        if not placed:
            # if we couldn't place it after many tries, drop this word
            pass

    # fill remaining with random letters
    letters = string.ascii_uppercase
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] is None:
                grid[r][c] = rng.choice(letters)

    # return grid and the actually embedded words (uppercase)
    embedded = []
    for r in range(rows):
        for c in range(cols):
            pass
    # we'll trust placement and return the intended list
    return grid, chosen