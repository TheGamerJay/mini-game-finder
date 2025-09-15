import os, re, csv
import sqlite3

ALNUM = re.compile(r"^[A-Za-z]{3,14}$")

def cx():
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("postgresql://"):
        import psycopg2
        return psycopg2.connect(url)
    else:
        # Use SQLite for local development
        return sqlite3.connect("instance/local.db")

def load_txt(p):
    seen = set()
    out = []
    for ln in open(p, encoding="utf-8"):
        w = ln.strip()
        if ALNUM.match(w):
            u = w.upper()
            if u not in seen:
                seen.add(u)
                out.append((u, len(u)))
    return out

def load_bad(p):
    if not p:
        return set()
    return {ln.strip().upper() for ln in open(p, encoding="utf-8") if ALNUM.match(ln.strip())}

def load_cat(p):
    rows = []
    if not p:
        return rows
    for word, key in csv.reader(open(p, encoding="utf-8")):
        word = word.strip().upper()
        key = key.strip().lower()
        if ALNUM.match(word) and key:
            rows.append((word, key))
    return rows

if __name__ == "__main__":
    import argparse
    pa = argparse.ArgumentParser()
    pa.add_argument("dictionary")
    pa.add_argument("--banned")
    pa.add_argument("--categories")
    a = pa.parse_args()

    words = load_txt(a.dictionary)
    banned = load_bad(a.banned)
    catrows = load_cat(a.categories)

    conn = cx()
    cur = conn.cursor()

    # Insert words
    for word, length in words:
        cur.execute("INSERT OR IGNORE INTO words(text,length) VALUES (?,?)", (word, length))

    # Insert banned words
    if banned:
        for b in banned:
            cur.execute("INSERT OR REPLACE INTO words(text,length,is_banned) VALUES (?,?,?)", (b, len(b), True))

    # Insert categories and word-category relationships
    if catrows:
        keys = sorted({k for _, k in catrows})
        for k in keys:
            cur.execute("INSERT OR IGNORE INTO categories(key,title) VALUES (?,?)", (k, k.replace("_", " ").title()))

        # Build word and category maps
        cur.execute("SELECT id, upper(text) FROM words")
        wmap = {t: i for i, t in cur.fetchall()}
        cur.execute("SELECT id, key FROM categories")
        cmap = {k: i for i, k in cur.fetchall()}

        # Insert word-category links
        for w, k in catrows:
            wid = wmap.get(w)
            cid = cmap.get(k)
            if wid and cid:
                cur.execute("INSERT OR IGNORE INTO word_categories(word_id,category_id) VALUES (?,?)", (wid, cid))

    conn.commit()
    cur.close()
    conn.close()
    print("Imported successfully!")