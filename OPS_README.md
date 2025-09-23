# ⚙️ OPS_README.md — Mini Word Finder Ops Guide

## 🔍 Smoke Tests (run after each deploy)

### Bash (Linux/Mac/CI)
    chmod +x smoke_test_api.sh
    ./smoke_test_api.sh http://localhost:5005

### PowerShell (Windows)
    .\smoke_test_api.ps1 -BaseUrl http://localhost:5005

### Python (Cross-platform)
    python smoke_test_api.py http://localhost:5005

Expected:
- /health → 200 JSON
- /api/word-finder/_ping → 200 JSON {ok:true}
- /api/word-finder/puzzle?mode=easy → 200 JSON {ok:true, mode:"easy"}
- /game/api/quota?game=mini_game_finder → 401 JSON {ok:false, error:"unauthorized"}

---

## ⚡ GitHub Actions (CI smoke)

Create `.github/workflows/smoke.yml` (see file below) and set repo secret `SMOKE_BASE_URL` to your staging/prod base URL.

---

## 🔐 Security Guardrails

- Exempt API routes from CSRF (e.g., `csrf.exempt(api_bp)`).
- Flask-Login `unauthorized_handler` & `needs_refresh_handler` return **JSON 401** for `/api/*` & `/game/api/*`.
- Use `@public` for read-only public APIs.
- SPA catch-all MUST NOT swallow `/api/*` or `/game/api/*`.

---

## 🚀 Deployment Checklist

1) Pre-Deploy
   - `curl <BASE>/__diag/rules` → verify `/api/*` routes present
   - Run DB migrations (or `db.create_all()` with app context)
   - `./smoke_test_api.sh <BASE>`

2) Deploy
   - Push to env, watch logs for URL map dump

3) Post-Deploy
   - Re-run smoke tests against env URL
   - Verify quota increments (0/5 → 1/5 after starting a game)
   - Verify mode persistence across "Next Game"

4) If Issues
   - `GET /__diag/match?path=/api/word-finder/puzzle&method=GET`
   - `GET /__diag/rules` to confirm registration
   - If auth issues: confirm `@public` and API gate skip are in place