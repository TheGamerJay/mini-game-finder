#!/usr/bin/env python3
import sqlite3

def check_riddle_stats():
    conn = sqlite3.connect('riddles.db')
    cursor = conn.cursor()

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM riddles")
    total = cursor.fetchone()[0]
    print(f"Total riddles: {total}")

    # Get count by difficulty
    cursor.execute("""
        SELECT difficulty, COUNT(*) as count
        FROM riddles
        GROUP BY difficulty
        ORDER BY difficulty
    """)

    print("\nRiddles by difficulty:")
    for difficulty, count in cursor.fetchall():
        percentage = (count / total) * 100
        print(f"{difficulty}: {count} ({percentage:.1f}%)")

    # Get sample riddles from each difficulty
    print("\nSample riddles:")
    for difficulty in ['easy', 'medium', 'hard']:
        cursor.execute("""
            SELECT question, answer
            FROM riddles
            WHERE difficulty = ?
            LIMIT 3
        """, (difficulty,))

        print(f"\n{difficulty.upper()} examples:")
        for i, (question, answer) in enumerate(cursor.fetchall(), 1):
            print(f"  {i}. Q: {question[:60]}...")
            print(f"     A: {answer}")

    conn.close()

if __name__ == "__main__":
    check_riddle_stats()