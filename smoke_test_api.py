import sys, json, urllib.request, urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"

def get(path):
    try:
        with urllib.request.urlopen(BASE + path) as r:
            return r.getcode(), r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return 0, str(e)

def must_code(path, expected):
    code, _ = get(path)
    if code == expected:
        print(f"✅ {path} → {code}")
    else:
        print(f"❌ {path} → {code} (expected {expected})"); sys.exit(1)

def must_json(path, predicate, desc):
    code, body = get(path)
    try:
        j = json.loads(body)
        if predicate(j):
            print(f"✅ {desc}")
        else:
            print(body); print(f"❌ {desc}"); sys.exit(1)
    except Exception:
        print(body); print(f"❌ {desc} (invalid JSON)"); sys.exit(1)

print(f"🔍 Smoke tests → {BASE}")

must_code("/health", 200)
must_code("/api/word-finder/_ping", 200)
must_code("/api/word-finder/puzzle?mode=easy", 200)
must_code("/game/api/quota?game=mini_word_finder", 401)

must_json("/api/word-finder/_ping", lambda j: j.get("ok") is True, "Ping ok:true")
must_json("/api/word-finder/puzzle?mode=easy", lambda j: j.get("ok") is True and j.get("mode")=="easy", "Puzzle mode=easy")
must_json("/game/api/quota?game=mini_word_finder", lambda j: j.get("ok") is False and j.get("error") in {"unauthorized","degraded_mode"}, "Quota protected")

print("🎉 All smoke tests passed!")
