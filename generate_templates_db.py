import os, json, hashlib, random, psycopg2
from psycopg2.extras import execute_values
from puzzles import generate_puzzle_from_words, MODE_CONFIG

def sha1(d):
    return hashlib.sha1(json.dumps(d, sort_keys=True).encode()).hexdigest()

def fetch_category_keys(conn, only=None):
    """Fetch available category keys from database"""
    with conn.cursor() as cur:
        if only:
            cur.execute("SELECT key FROM categories WHERE key = ANY(%s)", (only,))
        else:
            cur.execute("SELECT key FROM categories ORDER BY key")
        return [r[0] for r in cur.fetchall()]

def pick_words(conn, category, k, max_len):
    """Pick words from database for specific category"""
    with conn.cursor() as cur:
        cur.execute("""
          SELECT w.text
          FROM words w
          JOIN word_categories wc ON wc.word_id = w.id
          JOIN categories c ON c.id = wc.category_id
          WHERE c.key = %s AND w.is_banned = FALSE AND w.length <= %s
          ORDER BY random()
          LIMIT %s
        """, (category, max_len, k))
        return [r[0].upper() for r in cur.fetchall()]

def flush(cur, rows):
    """Flush rows to puzzle_bank table"""
    execute_values(cur, """
      INSERT INTO puzzle_bank(mode, category, title, words, grid, time_limit, seed, daily_date, active, puzzle_hash, answers)
      VALUES %s
      ON CONFLICT (puzzle_hash) DO NOTHING
    """, rows)

if __name__ == "__main__":
    import argparse, time
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-mode", type=int, default=50, help="templates per (mode,category)")
    ap.add_argument("--modes", default="easy,medium,hard")
    ap.add_argument("--categories", nargs="*", help="optional list of category keys")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    url = os.getenv("DATABASE_URL")
    assert url, "Set DATABASE_URL"

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    # Fetch categories from database
    cats = fetch_category_keys(conn, args.categories)
    if not cats:
        print("No categories found in database. Please import some categories first.")
        exit(1)

    modes = [m.strip() for m in args.modes.split(",")]
    rnd = random.Random(args.seed)
    buf = []
    total = 0

    print(f"Generating templates for categories: {cats}")
    print(f"Modes: {modes}")
    print(f"Templates per mode: {args.per_mode}")

    for cat in cats:
        print(f"Processing category: {cat}")
        for mode in modes:
            n = MODE_CONFIG[mode]["size"]
            k = MODE_CONFIG[mode]["words"]
            generated = 0

            for i in range(args.per_mode):
                seed = rnd.randint(1, 2_000_000_000)
                words = pick_words(conn, cat, k, n)

                if len(words) < k:
                    print(f"  Warning: Only found {len(words)} words for {cat}/{mode}, skipping")
                    continue

                P = generate_puzzle_from_words(mode, words, seed=seed)
                payload = {
                    "mode": mode,
                    "category": cat,
                    "words": P["words"],
                    "grid": P["grid"],
                    "time_limit": P["time_limit"],
                    "seed": P["seed"]
                }
                ph = sha1(payload)

                buf.append((
                    mode, cat, f"{cat.title()} {mode.title()} #{i+1}",
                    json.dumps(P["words"]), json.dumps(P["grid"]),
                    P["time_limit"], P["seed"], None, True, ph, json.dumps(P["answers"])
                ))
                generated += 1

                if len(buf) >= 200:
                    flush(cur, buf)
                    total += len(buf)
                    buf.clear()

            print(f"  Generated {generated} {mode} puzzles for {cat}")

    if buf:
        flush(cur, buf)
        total += len(buf)

    conn.commit()
    cur.close()
    conn.close()
    print(f"✓ Total templates inserted: {total}")