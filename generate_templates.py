import os, json, hashlib, random
import sqlite3
from puzzles import generate_puzzle

CATS = ["animals", "food", "sports", "cars", "home", "colors", "technology", "countries", "cities", "jobs", "school", "weather", "ocean", "desert", "space", "music", "movies", "plants", "tools", "clothes", "shapes"]

def sha1(d):
    return hashlib.sha1(json.dumps(d, sort_keys=True).encode()).hexdigest()

def flush(cur, rows):
    for row in rows:
        cur.execute("""
          INSERT OR IGNORE INTO puzzle_bank(mode,category,title,words,grid,time_limit,seed,daily_date,active,puzzle_hash,answers)
          VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, row)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--per-mode", type=int, default=50)
    p.add_argument("--modes", default="easy,medium,hard")
    a = p.parse_args()

    modes = [m.strip() for m in a.modes.split(",")]

    # Use SQLite for local development
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("postgresql://"):
        import psycopg2
        cx = psycopg2.connect(url)
    else:
        cx = sqlite3.connect("instance/local.db")

    cur = cx.cursor()
    buf = []

    for cat in CATS:
        for mode in modes:
            for i in range(a.per_mode):
                seed = random.randint(1, 2_000_000_000)
                P = generate_puzzle(mode, seed=seed, category=cat)
                payload = {"mode": mode, "category": cat, "words": P["words"], "grid": P["grid"], "time_limit": P["time_limit"], "seed": P["seed"]}
                ph = sha1(payload)

                buf.append((mode, cat, f"{cat.title()} {mode.title()} #{i+1}",
                           json.dumps(P["words"]), json.dumps(P["grid"]),
                           P["time_limit"], P["seed"], None, True, ph, json.dumps(P["answers"])))

                if len(buf) >= 200:
                    flush(cur, buf)
                    buf.clear()

    if buf:
        flush(cur, buf)

    cx.commit()
    cur.close()
    cx.close()
    print("Templates generated successfully!")