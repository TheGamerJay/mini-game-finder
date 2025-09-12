import random, string

WORDS_POOL = [
    "PYTHON","FLASK","RAILWAY","SERVER","CLIENT","CODE","DEBUG",
    "MUSIC","GAME","WORLD","CLOUD","ROUTE","TOKEN","STRIPE","WORDS"
]

DIRECTIONS = [(0,1),(0,-1),(1,0),(-1,0),(1,1),(-1,-1),(1,-1),( -1,1)]

def empty_grid(n): return [["" for _ in range(n)] for _ in range(n)]
def in_bounds(r,c,n): return 0 <= r < n and 0 <= c < n

def can_place(g,w,r,c,dr,dc):
    n=len(g)
    for i,ch in enumerate(w):
        rr,cc=r+dr*i,c+dc*i
        if not in_bounds(rr,cc,n): return False
        if g[rr][cc] not in ("", ch): return False
    return True

def _place_word_with_rng(g, w, rng):
    n=len(g)
    for _ in range(400):
        dr,dc = rng.choice(DIRECTIONS)
        r,c   = rng.randrange(n), rng.randrange(n)
        if can_place(g,w,r,c,dr,dc):
            for i,ch in enumerate(w):
                g[r+dr*i][c+dc*i]=ch
            return True
    return False

def generate_puzzle_seeded(seed: int, size=10, k=5):
    rng = random.Random(seed)
    pool=[w for w in WORDS_POOL if len(w)<=size]
    chosen=rng.sample(pool, k)
    grid=empty_grid(size)
    placed=[]
    for w in chosen:
        if _place_word_with_rng(grid, w, rng): placed.append(w)
    for r in range(size):
        for c in range(size):
            if grid[r][c]=="":
                grid[r][c]=rng.choice(string.ascii_uppercase)
    return grid, placed, chosen