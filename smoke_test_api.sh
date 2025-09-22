#!/bin/bash
# API Smoke Test - Verify no 302 redirects on API endpoints
# Usage: chmod +x smoke_test_api.sh && ./smoke_test_api.sh

API_BASE="http://127.0.0.1:5001"

echo "🔍 API Smoke Test - Checking for proper JSON responses (no 302 redirects)"
echo "============================================================================"

# Public GET endpoints - should return 200 JSON
echo "📊 Testing public endpoints..."
curl -s -w "Status: %{http_code}\n" "$API_BASE/api/leaderboard/top?game_code=word_finder" | tail -1
curl -s -w "Status: %{http_code}\n" "$API_BASE/api/leaderboard/word-finder" | tail -1
curl -s -w "Status: %{http_code}\n" "$API_BASE/api/leaderboard/word-finder/easy" | tail -1
curl -s -w "Status: %{http_code}\n" "$API_BASE/api/leaderboard/health" | tail -1

# Protected write endpoint - should return JSON 400/401 (not 302)
echo "🔒 Testing protected endpoints..."
curl -s -w "Status: %{http_code}\n" -X POST "$API_BASE/api/leaderboard/submit" | tail -1

# Regression test: ensure NO 302 responses for APIs
echo "🚫 Regression check - looking for any 302 redirects..."
REDIRECTS=$(curl -s -D - "$API_BASE/api/leaderboard/top" | awk 'tolower($0) ~ /^location:/ {print}')
if [ -z "$REDIRECTS" ]; then
    echo "✅ No redirects found - APIs returning proper JSON"
else
    echo "❌ REDIRECT DETECTED: $REDIRECTS"
fi

echo "============================================================================"
echo "✅ Smoke test complete. All API endpoints should return JSON, not HTML redirects."