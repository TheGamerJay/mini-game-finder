#!/usr/bin/env python3
"""
Test script for Redis leaderboard system
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_submit_score():
    """Test score submission to Redis leaderboard"""
    print("Testing Redis Leaderboard System...")

    # Test data
    test_data = {
        "user_id": "test_user_123",
        "display_name": "TestPlayer",
        "game_code": "mini_word_finder",
        "score": 5300  # Example score: 5 words * 1000 + 300 time bonus
    }

    try:
        # Submit score
        print(f"Submitting test score: {test_data}")
        response = requests.post(
            f"{BASE_URL}/api/leaderboard/submit",
            json=test_data,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Score submitted successfully!")
            print(f"   Rank: #{result.get('rank', 'N/A')}")
            print(f"   Season: {result.get('season_id', 'N/A')}")
            print(f"   Best this season: {result.get('best_season', 'N/A')}")
            print(f"   Best all-time: {result.get('best_all_time', 'N/A')}")
        else:
            print(f"Score submission failed: {response.status_code}")
            print(f"   Response: {response.text}")

        # Test top scores
        print("\nFetching top scores...")
        response = requests.get(
            f"{BASE_URL}/api/leaderboard/top",
            params={"game_code": "mini_word_finder", "n": 5},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Top scores retrieved!")
            print(f"   Season: {result.get('season_id', 'N/A')}")
            print(f"   Count: {result.get('count', 0)}")

            if result.get('rows'):
                print("   Top players:")
                for row in result['rows']:
                    print(f"     #{row['rank']} {row['display_name']} - {row['score']}")
            else:
                print("   No players yet")
        else:
            print(f"Top scores failed: {response.status_code}")

        # Test user rank
        print("\nFetching user rank...")
        response = requests.get(
            f"{BASE_URL}/api/leaderboard/rank",
            params={"game_code": "mini_word_finder", "user_id": "test_user_123"},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"User rank retrieved!")
            print(f"   Rank: #{result.get('rank', 'N/A')}")
            print(f"   Score: {result.get('score', 'N/A')}")
        else:
            print(f"User rank failed: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_submit_score()