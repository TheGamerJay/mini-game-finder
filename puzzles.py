import random
import os
import psycopg2

MODE_CONFIG = {
    "easy": {"size": 10, "words": 5, "time": None},
    "medium": {"size": 12, "words": 7, "time": 120},
    "hard": {"size": 14, "words": 10, "time": 180}
}

DIRS = {
    "E": (0, 1), "S": (1, 0), "W": (0, -1), "N": (-1, 0),
    "SE": (1, 1), "NE": (-1, 1), "SW": (1, -1), "NW": (-1, -1)
}

WORD_BANK = [
    "APPLE", "ROBOT", "TIGER", "LASER", "HOUSE", "MANGO", "OLIVE", "PEARL",
    "RIVER", "SMILE", "ULTRA", "VIOLET", "WHALE", "ZEBRA", "PIZZA", "BURGER",
    "EAGLE", "BEAR", "LION", "CODE", "DEBUG", "BUILD", "GRID", "ARRAY", "CLASS",
    "LOGIC", "STACK", "QUEUE", "LOOP", "PYTHON", "FLASK", "ROUTE", "LOGIN",
    "TOKEN", "RESET", "EMAIL", "SCORE", "WORDS", "CLOUD", "VALUE", "INDEX",
    "FIELD", "MODEL", "QUERY", "SEARCH", "LETTER", "PUZZLE", "RANDOM", "BOARD",
    "CLICK", "TIMER", "EASY", "MEDIUM", "HARD", "MUSIC", "DANCE", "SUNNY",
    "OCEAN", "FOREST", "MOUNTAIN", "SPACE", "PLANET", "STAR", "MOON", "EARTH"
]

# Category seed words for strict category matching
CATEGORY_SEEDS = {
    "animals": [
        "ANT","APE","BEAR","BISON","CAMEL","CAT","CHEETAH","COBRA","CRAB","DEER","DOG","DOLPHIN",
        "DONKEY","DUCK","EAGLE","ELK","FOX","FROG","GOAT","GOOSE","HAWK","HIPPO","HORSE","HYENA",
        "IGUANA","JAGUAR","KANGAROO","KOALA","LEMUR","LEOPARD","LLAMA","LION","LYNX","MOOSE","MOUSE",
        "OTTER","OWL","PANDA","PANTHER","PARROT","PENGUIN","PIG","PUMA","PYTHON","RABBIT","RACCOON",
        "RHINO","ROBIN","SEAL","SHARK","SHEEP","SNAKE","SPARROW","SQUID","SWAN","TIGER","TORTOISE",
        "TURTLE","WALRUS","WHALE","WOLF","ZEBRA"
    ],
    "sports": ["SOCCER","TENNIS","RUGBY","BOXING","GOLF","HOCKEY","CRICKET","ROWING","SURF","SKI"],
    "cars": ["ENGINE","BRAKE","COUPE","SEDAN","TURBO","GEARS","TIRES","MOTOR","AXLES","PEDAL"],
    "food": ["PIZZA","BURGER","MANGO","OLIVE","APPLE","BREAD","PASTA","SALAD","CANDY","TACO"],
    "home": ["CHAIR","TABLE","SOFA","LAMP","SHELF","PLANT","CURTAIN","WINDOW","STAIRS","CARPET"],
    "colors": ["VIOLET","ORANGE","CYAN","INDIGO","BLACK","WHITE","GREEN","YELLOW","PURPLE","BROWN"],
    "technology": ["LASER","ROBOT","RADAR","DRONE","PIXEL","MODEM","SENSOR","SERVER","BATTERY","SCREEN"],
}

# Category-specific word banks
CATEGORY_WORDS = {
    "cars": [
        "ENGINE", "WHEEL", "BRAKE", "SEDAN", "TRUCK", "HONDA", "TOYOTA", "FORD",
        "DIESEL", "GASOLINE", "TIRE", "BUMPER", "DOOR", "WINDOW", "MIRROR",
        "RADIO", "GEAR", "CLUTCH", "SPEED", "HIGHWAY", "ROAD", "DRIVE", "PARK",
        "FUEL", "OIL", "MOTOR", "PISTON", "VALVE", "SPARK", "PLUG", "BATTERY",
        "LIGHT", "SIGNAL", "HORN", "SEAT", "BELT", "AIRBAG", "TRUNK", "HOOD"
    ],
    "animals": [
        "TIGER", "EAGLE", "BEAR", "LION", "WHALE", "ZEBRA", "HORSE", "RABBIT",
        "ELEPHANT", "GIRAFFE", "MONKEY", "KANGAROO", "PENGUIN", "DOLPHIN", "SHARK",
        "SNAKE", "TURTLE", "FROG", "BIRD", "FISH", "CAT", "DOG", "COW", "PIG",
        "SHEEP", "GOAT", "CHICKEN", "DUCK", "GOOSE", "TURKEY", "DEER", "MOOSE"
    ],
    "food": [
        "APPLE", "MANGO", "OLIVE", "PIZZA", "BURGER", "BREAD", "CHEESE", "MILK",
        "BACON", "CHICKEN", "BEEF", "FISH", "RICE", "PASTA", "SOUP", "SALAD",
        "COOKIE", "CAKE", "PIE", "ICE", "CREAM", "CHOCOLATE", "CANDY", "FRUIT",
        "VEGETABLE", "CARROT", "POTATO", "TOMATO", "ONION", "GARLIC", "PEPPER"
    ],
    "nature": [
        "RIVER", "OCEAN", "FOREST", "MOUNTAIN", "TREE", "FLOWER", "GRASS", "ROCK",
        "STONE", "SAND", "BEACH", "LAKE", "POND", "STREAM", "VALLEY", "HILL",
        "CLOUD", "RAIN", "SNOW", "WIND", "SUN", "MOON", "STAR", "SKY", "EARTH",
        "PLANT", "LEAF", "BRANCH", "ROOT", "SEED", "SOIL", "WATER", "FIRE"
    ],
    "technology": [
        "ROBOT", "LASER", "CODE", "DEBUG", "BUILD", "GRID", "ARRAY", "CLASS",
        "LOGIC", "STACK", "QUEUE", "LOOP", "PYTHON", "FLASK", "ROUTE", "LOGIN",
        "TOKEN", "RESET", "EMAIL", "COMPUTER", "PHONE", "TABLET", "SCREEN",
        "KEYBOARD", "MOUSE", "INTERNET", "WEBSITE", "APP", "SOFTWARE", "HARDWARE"
    ],
    "sports": [
        "SOCCER", "FOOTBALL", "BASKETBALL", "TENNIS", "GOLF", "BASEBALL", "HOCKEY",
        "SWIMMING", "RUNNING", "CYCLING", "BOXING", "WRESTLING", "TRACK", "FIELD",
        "COURT", "BALL", "BAT", "RACKET", "GLOVE", "HELMET", "JERSEY", "SCORE",
        "GOAL", "POINT", "WIN", "LOSE", "TEAM", "PLAYER", "COACH", "GAME"
    ]
}

def _fits(G, r, c, dr, dc, w):
    n = len(G)
    rr = r + dr * (len(w) - 1)
    cc = c + dc * (len(w) - 1)
    if not (0 <= rr < n and 0 <= cc < n):
        return False
    for i, ch in enumerate(w):
        cell = G[r + dr * i][c + dc * i]
        if cell and cell != ch:
            return False
    return True

def _place(G, r, c, dr, dc, w):
    for i, ch in enumerate(w):
        G[r + dr * i][c + dc * i] = ch

def _build_key(rows, words):
    ans = {}
    grid = [list(r) for r in rows]
    n = len(grid)

    for W in [w.upper() for w in words]:
        hit = None
        for d, (dr, dc) in DIRS.items():
            for r in range(n):
                for c in range(n):
                    ok = True
                    for i, ch in enumerate(W):
                        rr, cc = r + dr * i, c + dc * i
                        if rr < 0 or cc < 0 or rr >= n or cc >= n or grid[rr][cc] != ch:
                            ok = False
                            break
                    if ok:
                        hit = {"start": [r, c], "dir": d, "len": len(W)}
                        break
                if hit:
                    break
            if hit:
                break

        if not hit:
            # Try reverse
            W2 = W[::-1]
            for d, (dr, dc) in DIRS.items():
                for r in range(n):
                    for c in range(n):
                        ok = True
                        for i, ch in enumerate(W2):
                            rr, cc = r + dr * i, c + dc * i
                            if rr < 0 or cc < 0 or rr >= n or cc >= n or grid[rr][cc] != ch:
                                ok = False
                                break
                        if ok:
                            hit = {"start": [r, c], "dir": d, "len": len(W2)}
                            break
                    if hit:
                        break
                if hit:
                    break

        if hit:
            ans[W] = hit
    return ans

def _choose_words_from_db(category, k, max_len):
    import os, psycopg2
    url=os.getenv("DATABASE_URL")
    if not url: return []
    q = """
      SELECT w.text
      FROM words w
      JOIN word_categories wc ON wc.word_id = w.id
      JOIN categories c ON c.id = wc.category_id
      WHERE c.key = %s AND w.is_banned = FALSE AND w.length <= %s
      ORDER BY random() LIMIT %s
    """
    try:
        cx=psycopg2.connect(url); cur=cx.cursor()
        cur.execute(q, (category, max_len, k))
        rows=cur.fetchall(); cur.close(); cx.close()
        return [r[0].upper() for r in rows]
    except Exception:
        return []

def _topup_with_category_seeds(category, have, k, max_len):
    pool = [w for w in CATEGORY_SEEDS.get(category, []) if len(w) <= max_len and w not in have]
    out = list(have)
    for w in pool:
        if len(out) >= k: break
        out.append(w)
    return out

def generate_puzzle_from_words(mode, words, seed=None):
    """Generate puzzle from specific word list"""
    cfg = MODE_CONFIG[mode]
    n = cfg["size"]
    rnd = random.Random(seed)

    words = [w.upper() for w in words if len(w) <= n]
    words = list(dict.fromkeys(words))  # unique, preserve order
    k = min(len(words), cfg["words"])
    words = words[:k]

    G = [[""] * n for _ in range(n)]

    for w in words:
        placed = False
        dirs = list(DIRS.values())
        rnd.shuffle(dirs)

        for _ in range(400):
            r, c = rnd.randrange(n), rnd.randrange(n)
            dr, dc = rnd.choice(dirs)
            if _fits(G, r, c, dr, dc, w):
                _place(G, r, c, dr, dc, w)
                placed = True
                break

        if not placed:
            # Try horizontal placement as fallback
            for rr in range(n):
                for cc in range(n - len(w) + 1):
                    if _fits(G, rr, cc, 0, 1, w):
                        _place(G, rr, cc, 0, 1, w)
                        placed = True
                        break
                if placed:
                    break

    # Fill empty cells with random letters
    for r in range(n):
        for c in range(n):
            if not G[r][c]:
                G[r][c] = rnd.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    rows = ["".join(r) for r in G]
    return {
        "grid": rows,
        "words": words,
        "mode": mode,
        "time_limit": cfg["time"],
        "seed": seed,
        "answers": _build_key(rows, words)
    }

def generate_puzzle(mode, seed=None, category=None):
    cfg=MODE_CONFIG[mode]; n=cfg["size"]; k=cfg["words"]
    if category:
        words = _choose_words_from_db(category, k, n)
        words = _topup_with_category_seeds(category, words, k, n)
        if len(words) < k and words:
            # if still short, repeat from seeds to fill (keeps theme strict)
            for w in CATEGORY_SEEDS.get(category, []):
                if len(words) >= k: break
                if len(w) <= n and w not in words: words.append(w)
        if not words:
            # last resort: seeds only (still on-topic)
            words = _topup_with_category_seeds(category, [], k, n)
        return generate_puzzle_from_words(mode, words[:k], seed=seed)

    # No category selected → generic
    candidates=[w for w in WORD_BANK if len(w) <= cfg["size"]]
    random.Random(seed).shuffle(candidates)
    return generate_puzzle_from_words(mode, candidates[:k], seed=seed)

# Legacy function for compatibility
def make_puzzle(rows, cols, words_count, seed=None, dictionary=None):
    """Legacy function for backward compatibility"""
    mode = "easy" if rows <= 10 else "medium" if rows <= 12 else "hard"
    puzzle = generate_puzzle(mode, seed=seed)

    # Convert to old format
    grid = [[ch for ch in row] for row in puzzle["grid"]]
    words = puzzle["words"]

    return grid, words