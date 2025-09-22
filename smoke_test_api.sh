#\!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:5000}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing $1"; exit 2; }; }
need curl
need jq

echo "🔍 Smoke tests → $BASE_URL"

pass() { echo "✅ $1"; }
fail() { echo "❌ $1"; exit 1; }

check_code() {
  local path="$1" expected="$2"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL$path") || true
  [[ "$code" == "$expected" ]] && pass "$path → $code" || fail "$path → $code (expected $expected)"
}

check_json() {
  local path="$1" jqexpr="$2" desc="$3"
  local body
  body=$(curl -sS "$BASE_URL$path" || true)
  echo "$body" | jq -e "$jqexpr" >/dev/null 2>&1     && pass "$desc"     || { echo "Body:"; echo "$body"; fail "$desc (jq failed: $jqexpr)"; }
}

# Liveness & routing
check_code "/health" 200
check_code "/api/word-finder/_ping" 200
check_code "/api/word-finder/puzzle?mode=easy" 200
check_code "/game/api/quota?game=mini_word_finder" 401

# JSON semantics
check_json "/api/word-finder/_ping" '.ok == true' "Ping returns ok:true"
check_json "/api/word-finder/puzzle?mode=easy" '.ok == true and .mode=="easy"' "Puzzle returns mode:easy"
check_json "/game/api/quota?game=mini_word_finder" '.ok == false and (.error=="unauthorized" or .error=="degraded_mode")' "Quota protected (401)"

echo "🎉 All smoke tests passed\!"
