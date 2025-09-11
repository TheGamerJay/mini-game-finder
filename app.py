from flask import Flask, render_template
import random
import string

app = Flask(__name__)

GRID_SIZE = 10
CANDIDATE_WORDS = [
    "PYTHON","FLASK","RAILWAY","SERVER","CLIENT","CODE","DEBUG",
    "MUSIC","GAME","WORLD","CLOUD","ROUTE","TOKEN","STRIPE","WORDS"
]

DIRECTIONS = [
    (0, 1),   # →
    (0, -1),  # ←
    (1, 0),   # ↓
    (-1, 0),  # ↑
    (1, 1),   # ↘
    (-1, -1), # ↖
    (1, -1),  # ↙
    (-1, 1),  # ↗
]

def empty_grid(n):
    return [["" for _ in range(n)] for _ in range(n)]

def in_bounds(r, c, n):
    return 0 <= r < n and 0 <= c < n

def can_place(grid, word, r, c, dr, dc):
    n = len(grid)
    for i, ch in enumerate(word):
        rr, cc = r + dr*i, c + dc*i
        if not in_bounds(rr, cc, n):
            return False
        cell = grid[rr][cc]
        if cell not in ("", ch):
            return False
    return True

def place_word(grid, word):
    n = len(grid)
    attempts = 400
    while attempts > 0:
        dr, dc = random.choice(DIRECTIONS)
        # choose a start such that word fits within bounds
        r = random.randrange(n)
        c = random.randrange(n)
        if can_place(grid, word, r, c, dr, dc):
            for i, ch in enumerate(word):
                rr, cc = r + dr*i, c + dc*i
                grid[rr][cc] = ch
            return True
        attempts -= 1
    return False

def generate_puzzle(size=GRID_SIZE, k=5):
    # choose words that actually fit the grid
    words = [w for w in CANDIDATE_WORDS if len(w) <= size]
    chosen = random.sample(words, k)

    grid = empty_grid(size)
    placed = []
    for w in chosen:
        if place_word(grid, w):
            placed.append(w)
        else:
            # if a word failed to place, pick another one
            remaining = [x for x in words if x not in chosen and x not in placed and len(x) <= size]
            for alt in remaining:
                if place_word(grid, alt):
                    placed.append(alt)
                    break

    # fill blanks with random letters
    for r in range(size):
        for c in range(size):
            if grid[r][c] == "":
                grid[r][c] = random.choice(string.ascii_uppercase)

    return grid, placed

@app.route("/")
def index():
    grid, words = generate_puzzle()
    return render_template("index.html", grid=grid, words=words)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)