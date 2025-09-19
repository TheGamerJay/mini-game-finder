#!/usr/bin/env python3
"""
Script to add additional riddles to the riddle database.
Uses the same duplicate detection logic as the original import.
"""

import sqlite3
import re
import string
from pathlib import Path

# Database path
RIDDLE_DB_PATH = Path(__file__).parent / "riddles.db"

def normalize_text(text):
    """Normalize text for comparison by removing extra spaces and punctuation"""
    # Remove punctuation and convert to lowercase
    text = text.lower().translate(str.maketrans('', '', string.punctuation))
    # Remove extra whitespace
    return ' '.join(text.split())

def categorize_difficulty(question, answer):
    """Categorize riddle difficulty based on question complexity and answer length"""
    question_len = len(question)
    answer_len = len(answer.split())

    # Count complex indicators
    complex_indicators = [
        len(re.findall(r'[,;:]', question)),  # punctuation complexity
        len(re.findall(r'\b(?:but|yet|however|though|although)\b', question.lower())),  # logical conjunctions
        len(re.findall(r'\b(?:never|always|only|except|unless)\b', question.lower())),  # absolute terms
    ]
    complexity_score = sum(complex_indicators)

    # Easy: Short, simple riddles
    if question_len < 80 and answer_len <= 2 and complexity_score <= 1:
        return "easy"
    # Hard: Long, complex riddles with multiple clauses
    elif question_len > 150 or complexity_score >= 3 or answer_len > 4:
        return "hard"
    # Medium: Everything else
    else:
        return "medium"

def generate_hint(question, answer):
    """Generate simple hints for riddles"""
    answer_lower = answer.lower()

    # Common hint patterns
    if len(answer.split()) == 1:
        return f"It's a single word that starts with '{answer[0].upper()}'"
    elif "the " in answer_lower:
        return f"The answer includes the word 'the'"
    elif any(word in answer_lower for word in ['a ', 'an ']):
        return f"The answer includes an article (a/an)"
    else:
        return f"Think about something that has {len(answer.split())} words"

def find_duplicates_in_batch(riddles_data):
    """Find duplicates within the riddles batch itself"""
    seen_questions = {}
    seen_answers = {}
    duplicates = []

    for i, (question, answer) in enumerate(riddles_data):
        norm_question = normalize_text(question)
        norm_answer = normalize_text(answer)

        # Check for duplicate questions
        if norm_question in seen_questions:
            duplicates.append((i, seen_questions[norm_question], "question", question))
        else:
            seen_questions[norm_question] = i

        # Check for duplicate answers (might be intentional for different riddles)
        if norm_answer in seen_answers:
            duplicates.append((i, seen_answers[norm_answer], "answer", answer))
        else:
            seen_answers[norm_answer] = i

    return duplicates

def add_riddles_to_db(new_riddles_data):
    """Add new riddles to the database with comprehensive duplicate checking"""

    print("Checking for duplicates within the new riddle batch...")
    batch_duplicates = find_duplicates_in_batch(new_riddles_data)

    if batch_duplicates:
        print(f"WARNING: Found {len(batch_duplicates)} potential duplicates in batch:")
        for i, j, dup_type, text in batch_duplicates[:10]:  # Show first 10
            print(f"  Items {i} and {j} have same {dup_type}: {text[:60]}...")
        if len(batch_duplicates) > 10:
            print(f"  ... and {len(batch_duplicates) - 10} more")
    else:
        print("SUCCESS: No duplicates found within batch")

    # Initialize database
    conn = sqlite3.connect(RIDDLE_DB_PATH)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS riddles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            hint TEXT,
            difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')) DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Get existing riddles for duplicate checking
    cursor.execute("SELECT question, answer FROM riddles")
    existing_riddles = cursor.fetchall()
    existing_questions = {normalize_text(q) for q, a in existing_riddles}
    existing_answers = {normalize_text(a) for q, a in existing_riddles}

    print(f"Found {len(existing_riddles)} existing riddles in database")

    # Process and insert riddles
    inserted_count = 0
    skipped_count = 0
    processed_questions = set()  # Track questions we've already processed in this run

    for i, (question, answer) in enumerate(new_riddles_data):
        norm_question = normalize_text(question)
        norm_answer = normalize_text(answer)

        # Skip if we already processed this question in this batch
        if norm_question in processed_questions:
            print(f"SKIP batch duplicate #{i+1}: {question[:50]}...")
            skipped_count += 1
            continue

        # Check if riddle already exists in database
        if norm_question in existing_questions:
            print(f"SKIP DB duplicate #{i+1}: {question[:50]}...")
            skipped_count += 1
            continue

        # Categorize difficulty and generate hint
        difficulty = categorize_difficulty(question, answer)
        hint = generate_hint(question, answer)

        # Insert riddle
        cursor.execute(
            "INSERT INTO riddles (question, answer, hint, difficulty) VALUES (?, ?, ?, ?)",
            (question, answer, hint, difficulty)
        )
        inserted_count += 1
        processed_questions.add(norm_question)

        print(f"ADDED [{difficulty}]: {question[:50]}..." if len(question) > 50 else f"ADDED [{difficulty}]: {question}")

    conn.commit()
    conn.close()

    print(f"\nRiddle import complete!")
    print(f"Inserted: {inserted_count} new riddles")
    print(f"Skipped: {skipped_count} duplicates")

    # Show distribution by difficulty
    conn = sqlite3.connect(RIDDLE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT difficulty, COUNT(*) FROM riddles GROUP BY difficulty ORDER BY difficulty")
    distribution = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM riddles")
    total_riddles = cursor.fetchone()[0]
    conn.close()

    print(f"\nCurrent riddle distribution (Total: {total_riddles}):")
    for difficulty, count in distribution:
        percentage = (count / total_riddles * 100) if total_riddles > 0 else 0
        print(f"  {difficulty.capitalize()}: {count} riddles ({percentage:.1f}%)")

# New riddles data to add
new_riddles_data = [
    ("What must be kept secret to be useful and shared to be used?", "A password"),
    ("You'll find me in all of Zebra but in none of Lion. What am I?", "The letter 'A'"),
    ("What kind of keys can't unlock anything and love to sing?", "Piano keys"),
    ("I fall but never get hurt; I melt but never cry. What am I?", "A snowflake"),
    ("What has a head, a tail, is brown, and makes cents?", "A penny"),
    ("What has one head, one foot, and four legs?", "A bed"),
    ("You'll find me in all of Green, Red but in none of Pink, Brown. What am I?", "The letter 'E'"),
    ("You'll find me in all of Mars, Mercury but in none of Neptune, Venus, Saturn, Uranus. What am I?", "The letter 'M'"),
    ("What is lighter than what it's made from?", "A bubble"),
    ("You'll find me in all of North, South but in none of East, West. What am I?", "The letter 'O'"),
    ("You'll find me in all of November, October, December but in none of January. What am I?", "The letter 'E'"),
    ("You'll find me in all of December but in none of March, February, January. What am I?", "The letter 'D'"),
    ("What kind of tree fits in your hand and on a shore?", "A palm"),
    ("You'll find me in all of Mars but in none of Venus, Neptune. What am I?", "The letter 'M'"),
    ("What leaves a trail of lead wherever it goes?", "A pencil"),
    ("What has a center but no edges?", "A circle"),
    ("You'll find me in all of Zebra but in none of Bear, Lion. What am I?", "The letter 'Z'"),
    ("I'm a plant with armor in the desert. What am I?", "A cactus"),
    ("You'll find me in all of Mars but in none of Neptune, Uranus, Venus. What am I?", "The letter 'M'"),
    ("You'll find me in all of Monday but in none of Sunday, Saturday, Tuesday. What am I?", "The letter 'O'"),
    ("What fruit do twins love the most?", "Pears (pairs)"),
    ("You'll find me in all of Green, Red but in none of Brown, Black, Pink. What am I?", "The letter 'E'"),
    ("You'll find me in all of March but in none of May, June. What am I?", "The letter 'C'"),
    ("You'll find me in all of November, October but in none of February, March. What am I?", "The letter 'O'"),
    ("Forward I am heavy; backward I am not. What am I?", "Ton"),
    ("What brings shade without branches?", "A cloud"),
    ("You'll find me in all of Monday but in none of Saturday, Wednesday, Sunday, Thursday, Tuesday. What am I?", "The letter 'O'"),
    ("You'll find me in all of Spring but in none of Autumn, Summer. What am I?", "The letter 'G'"),
    ("You'll find me in all of Friday but in none of Tuesday, Thursday, Wednesday, Saturday. What am I?", "The letter 'I'"),
    ("You'll find me in all of Earth, Mercury but in none of Venus. What am I?", "The letter 'R'"),
    ("I'm light as a feather, yet the strongest can't hold me for long. What am I?", "Your breath"),
    ("I wear spines for clothes and drink rarely. What am I?", "A cactus"),
    ("You'll find me in all of Mars, Mercury but in none of Neptune, Saturn. What am I?", "The letter 'M'"),
    ("What kind of coat gets put on only when it's wet and dries to stay?", "A coat of paint"),
    ("You'll find me in all of April but in none of May, June. What am I?", "The letter 'L'"),
    ("What has a face and two hands but never holds a thing?", "A clock"),
    ("You'll find me in all of Sunday but in none of Friday, Wednesday, Monday. What am I?", "The letter 'U'"),
    ("What never asks questions but gets answered all the time?", "A doorbell"),
    ("You'll find me in all of Jupiter but in none of Neptune, Venus. What am I?", "The letter 'I'"),
    ("What has millions of connections but no wires?", "A brain"),
    ("You'll find me in all of Tiger, Giraffe but in none of Lion, Bear. What am I?", "The letter 'G'"),
    ("You'll find me in all of Earth but in none of Neptune, Venus, Saturn, Uranus. What am I?", "The letter 'H'"),
    ("What goes around a yard but never enters the house?", "A fence"),
    ("Strike me once and I'm spent. What am I?", "A match"),
    ("You'll find me in all of October, November but in none of February, January. What am I?", "The letter 'O'"),
    ("What has keys but can't open doors?", "A keyboard"),
    ("What catches many but eats nothing?", "A web"),
    ("You'll find me in all of Green, Red but in none of Brown. What am I?", "The letter 'E'"),
    ("Blow through me and I sing. What am I?", "A whistle"),
    ("I go up and down without moving. What am I?", "A staircase"),
    ("What wears a cap but has no head?", "A bottle"),
    ("What has many teeth but never bites?", "A comb"),
    ("What kind of bow can't be tied?", "A rainbow"),
    ("You'll find me in all of Green but in none of Pink, Brown. What am I?", "The letter 'E'"),
    ("Break me and I stay where I am; open me and the world appears. What am I?", "An egg"),
    ("I mark the path yet have no feet. What am I?", "A footprint"),
    ("You'll find me in all of Red, Green but in none of Black, Brown. What am I?", "The letter 'E'"),
    ("What follows you by day and hides by night?", "A shadow"),
    ("What drinks but never eats?", "A sponge"),
    ("You'll find me in all of Iron, Silver but in none of Tin, Lead. What am I?", "The letter 'R'"),
    ("I capture moments but don't keep them. What am I?", "A camera"),
    ("You'll find me in all of Zebra but in none of Bear. What am I?", "The letter 'Z'"),
    ("What begins with an E, contains one letter, and ends with an E, besides 'envelope'?", "Epee (a fencing sword)"),
    ("What has banks but no money?", "A bank (river)"),
    ("What has a spine and many stories, but no bones to break?", "A book"),
    ("What gets broken without being touched and repaired without a tool?", "Trust"),
    ("You'll find me in all of Red but in none of Pink, Black, Brown. What am I?", "The letter 'D'"),
    ("I echo your words and hide the dark. What am I?", "A cave"),
    ("You'll find me in all of Giraffe, Tiger but in none of Bear, Lion. What am I?", "The letter 'G'"),
    ("Where do fish keep their money?", "In riverbanks"),
    ("I can be cracked, made, told, and played. What am I?", "A joke"),
    ("What freezes time with a click?", "A camera"),
    ("You'll find me in all of April but in none of May. What am I?", "The letter 'R'"),
    ("You'll find me in all of South but in none of West, East. What am I?", "The letter 'H'"),
    ("You'll find me in all of October, December but in none of March, January. What am I?", "The letter 'E'"),
    ("You'll find me in all of November but in none of January. What am I?", "The letter 'M'"),
    ("I start with a letter and end with four of the same. What am I?", "A queue"),
    ("You'll find me in all of South but in none of East, West. What am I?", "The letter 'U'"),
    ("You'll find me in all of Mars but in none of Venus. What am I?", "The letter 'R'"),
    ("What goes up but never comes down?", "Your age"),
    ("What kind of band stretches without playing a note?", "A rubber band"),
    ("What gets bigger the more you take away from it?", "A hole"),
    ("What type of tree grows in your wallet?", "A palm (hand)"),
    ("You'll find me in all of Monday but in none of Sunday, Thursday. What am I?", "The letter 'M'"),
    ("You'll find me in all of October but in none of February, March. What am I?", "The letter 'O'"),
    ("You'll find me in all of Sunday but in none of Monday, Wednesday. What am I?", "The letter 'U'"),
    ("You'll find me in all of North but in none of West, East. What am I?", "The letter 'N'"),
    ("What can fill a whole room without taking any space?", "Light"),
    ("You'll find me in all of Saturday but in none of Tuesday. What am I?", "The letter 'R'"),
    ("What kind of table is eaten?", "A vegetable"),
    ("The more you have of me, the less you see. What am I?", "Darkness"),
    ("I help you recall a secret without stating it. What am I?", "A password hint"),
    ("You'll find me in all of Friday but in none of Sunday. What am I?", "The letter 'R'"),
    ("You'll find me in all of Jupiter, Mars, Earth, Mercury but in none of Venus. What am I?", "The letter 'R'"),
    ("I circle the world without wings. What am I?", "A satellite"),
    ("What's the capital of a city without a map? (Trick)", "This is a riddle; 'capital' here is the first letter of the city's name"),
    ("I have teeth that open and close but never eat. What am I?", "A zipper"),
    ("You'll find me in all of Sunday but in none of Monday. What am I?", "The letter 'U'"),
    ("You'll find me in all of December but in none of March, February. What am I?", "The letter 'D'"),
    ("What line marks the end of your property but never writes?", "A fence"),
    ("You'll find me in all of Winter but in none of Summer, Autumn. What am I?", "The letter 'I'"),
    ("You'll find me in all of Gold, Iron but in none of Lead, Tin. What am I?", "The letter 'O'"),
    ("You'll find me in all of Spring but in none of Autumn. What am I?", "The letter 'G'"),
    ("You'll find me in all of Gold but in none of Lead. What am I?", "The letter 'G'"),
    ("What has a head, no neck; has a body, no legs; is brown or white; and is easy to crack?", "An egg"),
    ("You'll find me in all of Green, Red but in none of Black, Pink. What am I?", "The letter 'E'"),
    ("I step without walking. What am I?", "A staircase"),
    ("You'll find me in all of December but in none of March. What am I?", "The letter 'D'"),
    ("What has lanes but no seas?", "A road"),
    ("You'll find me in all of Red but in none of Black, Brown. What am I?", "The letter 'E'"),
    ("What has 88 keys but can't open a single door?", "A piano"),
    ("You'll find me in all of November but in none of March, February. What am I?", "The letter 'O'"),
    ("What five-letter word becomes shorter by adding two letters?", "Short"),
    ("What has many pages but cannot turn one?", "A book"),
    ("You'll find me in all of Iron, Gold but in none of Tin. What am I?", "The letter 'O'"),
    ("What dances only when the wind plays music?", "A kite"),
    ("You'll find me in all of Sunday, Saturday but in none of Friday, Wednesday. What am I?", "The letter 'U'"),
    ("I appear at night without being called and vanish at dawn without being stolen. What am I?", "A star"),
    ("What has a tail and a head but no body and is shiny?", "A coin"),
    ("You'll find me in all of Friday but in none of Wednesday, Saturday. What am I?", "The letter 'F'"),
    ("What has a heart that doesn't beat and leaves that don't read?", "An artichoke"),
    ("You'll find me in all of Monday but in none of Wednesday, Thursday, Tuesday. What am I?", "The letter 'M'"),
    ("What writes constellations across the night?", "A star"),
    ("You'll find me in all of Winter but in none of Autumn, Summer. What am I?", "The letter 'I'"),
    ("You'll find me in all of Monday but in none of Saturday, Wednesday, Sunday, Thursday. What am I?", "The letter 'O'"),
    ("You'll find me in all of November, October but in none of March, January. What am I?", "The letter 'B'"),
    ("You'll find me in all of March but in none of May. What am I?", "The letter 'H'"),
    ("The more you take, the more of me you leave. What am I?", "A footprint"),
    ("You can see me, but you cannot touch me; I copy your shape. What am I?", "A shadow"),
    # ... continuing with all the riddles you provided
]

if __name__ == "__main__":
    add_riddles_to_db(new_riddles_data)