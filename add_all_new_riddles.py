#!/usr/bin/env python3
"""
Complete script to add all new riddles with comprehensive duplicate detection
"""

import sqlite3
import re
import string
from pathlib import Path

# Database path
RIDDLE_DB_PATH = Path(__file__).parent / "riddles.db"

def normalize_text(text):
    """Normalize text for comparison by removing extra spaces and punctuation"""
    text = text.lower().translate(str.maketrans('', '', string.punctuation))
    return ' '.join(text.split())

def categorize_difficulty(question, answer):
    """Categorize riddle difficulty based on question complexity and answer length"""
    question_len = len(question)
    answer_len = len(answer.split())

    complex_indicators = [
        len(re.findall(r'[,;:]', question)),
        len(re.findall(r'\b(?:but|yet|however|though|although)\b', question.lower())),
        len(re.findall(r'\b(?:never|always|only|except|unless)\b', question.lower())),
    ]
    complexity_score = sum(complex_indicators)

    if question_len < 80 and answer_len <= 2 and complexity_score <= 1:
        return "easy"
    elif question_len > 150 or complexity_score >= 3 or answer_len > 4:
        return "hard"
    else:
        return "medium"

def generate_hint(question, answer):
    """Generate simple hints for riddles"""
    answer_lower = answer.lower()
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

        if norm_question in seen_questions:
            duplicates.append((i, seen_questions[norm_question], "question", question))
        else:
            seen_questions[norm_question] = i

        if norm_answer in seen_answers:
            duplicates.append((i, seen_answers[norm_answer], "answer", answer))
        else:
            seen_answers[norm_answer] = i

    return duplicates

# All new riddles to add
NEW_RIDDLES = [
    ("What must be kept secret to be useful and shared to be used?", "A password"),
    ("You'll find me in all of Zebra but in none of Lion. What am I?", "The letter A"),
    ("What kind of keys can't unlock anything and love to sing?", "Piano keys"),
    ("I fall but never get hurt; I melt but never cry. What am I?", "A snowflake"),
    ("What has a head, a tail, is brown, and makes cents?", "A penny"),
    ("What has one head, one foot, and four legs?", "A bed"),
    ("You'll find me in all of Green, Red but in none of Pink, Brown. What am I?", "The letter E"),
    ("You'll find me in all of Mars, Mercury but in none of Neptune, Venus, Saturn, Uranus. What am I?", "The letter M"),
    ("What is lighter than what it's made from?", "A bubble"),
    ("You'll find me in all of North, South but in none of East, West. What am I?", "The letter O"),
    ("You'll find me in all of November, October, December but in none of January. What am I?", "The letter E"),
    ("You'll find me in all of December but in none of March, February, January. What am I?", "The letter D"),
    ("What kind of tree fits in your hand and on a shore?", "A palm"),
    ("You'll find me in all of Mars but in none of Venus, Neptune. What am I?", "The letter M"),
    ("What leaves a trail of lead wherever it goes?", "A pencil"),
    ("What has a center but no edges?", "A circle"),
    ("You'll find me in all of Zebra but in none of Bear, Lion. What am I?", "The letter Z"),
    ("I'm a plant with armor in the desert. What am I?", "A cactus"),
    ("You'll find me in all of Mars but in none of Neptune, Uranus, Venus. What am I?", "The letter M"),
    ("You'll find me in all of Monday but in none of Sunday, Saturday, Tuesday. What am I?", "The letter O"),
    ("What fruit do twins love the most?", "Pears (pairs)"),
    ("You'll find me in all of Green, Red but in none of Brown, Black, Pink. What am I?", "The letter E"),
    ("You'll find me in all of March but in none of May, June. What am I?", "The letter C"),
    ("You'll find me in all of November, October but in none of February, March. What am I?", "The letter O"),
    ("Forward I am heavy; backward I am not. What am I?", "Ton"),
    ("What brings shade without branches?", "A cloud"),
    ("You'll find me in all of Monday but in none of Saturday, Wednesday, Sunday, Thursday, Tuesday. What am I?", "The letter O"),
    ("You'll find me in all of Spring but in none of Autumn, Summer. What am I?", "The letter G"),
    ("You'll find me in all of Friday but in none of Tuesday, Thursday, Wednesday, Saturday. What am I?", "The letter I"),
    ("You'll find me in all of Earth, Mercury but in none of Venus. What am I?", "The letter R"),
    ("I'm light as a feather, yet the strongest can't hold me for long. What am I?", "Your breath"),
    ("I wear spines for clothes and drink rarely. What am I?", "A cactus"),
    ("You'll find me in all of Mars, Mercury but in none of Neptune, Saturn. What am I?", "The letter M"),
    ("What kind of coat gets put on only when it's wet and dries to stay?", "A coat of paint"),
    ("You'll find me in all of April but in none of May, June. What am I?", "The letter L"),
    ("What has a face and two hands but never holds a thing?", "A clock"),
    ("You'll find me in all of Sunday but in none of Friday, Wednesday, Monday. What am I?", "The letter U"),
    ("What never asks questions but gets answered all the time?", "A doorbell"),
    ("You'll find me in all of Jupiter but in none of Neptune, Venus. What am I?", "The letter I"),
    ("What has millions of connections but no wires?", "A brain"),
    ("You'll find me in all of Tiger, Giraffe but in none of Lion, Bear. What am I?", "The letter G"),
    ("You'll find me in all of Earth but in none of Neptune, Venus, Saturn, Uranus. What am I?", "The letter H"),
    ("What goes around a yard but never enters the house?", "A fence"),
    ("Strike me once and I'm spent. What am I?", "A match"),
    ("You'll find me in all of October, November but in none of February, January. What am I?", "The letter O"),
    ("What has keys but can't open doors?", "A keyboard"),
    ("What catches many but eats nothing?", "A web"),
    ("You'll find me in all of Green, Red but in none of Brown. What am I?", "The letter E"),
    ("Blow through me and I sing. What am I?", "A whistle"),
    ("I go up and down without moving. What am I?", "A staircase"),
    ("What wears a cap but has no head?", "A bottle"),
    ("What has many teeth but never bites?", "A comb"),
    ("What kind of bow can't be tied?", "A rainbow"),
    ("You'll find me in all of Green but in none of Pink, Brown. What am I?", "The letter E"),
    ("Break me and I stay where I am; open me and the world appears. What am I?", "An egg"),
    ("I mark the path yet have no feet. What am I?", "A footprint"),
    ("You'll find me in all of Red, Green but in none of Black, Brown. What am I?", "The letter E"),
    ("What follows you by day and hides by night?", "A shadow"),
    ("What drinks but never eats?", "A sponge"),
    ("You'll find me in all of Iron, Silver but in none of Tin, Lead. What am I?", "The letter R"),
    ("I capture moments but don't keep them. What am I?", "A camera"),
    ("You'll find me in all of Zebra but in none of Bear. What am I?", "The letter Z"),
    ("What begins with an E, contains one letter, and ends with an E, besides 'envelope'?", "Epee (a fencing sword)"),
    ("What has banks but no money?", "A bank (river)"),
    ("What has a spine and many stories, but no bones to break?", "A book"),
    ("What gets broken without being touched and repaired without a tool?", "Trust"),
    ("You'll find me in all of Red but in none of Pink, Black, Brown. What am I?", "The letter D"),
    ("I echo your words and hide the dark. What am I?", "A cave"),
    ("You'll find me in all of Giraffe, Tiger but in none of Bear, Lion. What am I?", "The letter G"),
    ("Where do fish keep their money?", "In riverbanks"),
    ("I can be cracked, made, told, and played. What am I?", "A joke"),
    ("What freezes time with a click?", "A camera"),
    ("You'll find me in all of April but in none of May. What am I?", "The letter R"),
    ("You'll find me in all of South but in none of West, East. What am I?", "The letter H"),
    ("You'll find me in all of October, December but in none of March, January. What am I?", "The letter E"),
    ("You'll find me in all of November but in none of January. What am I?", "The letter M"),
    ("I start with a letter and end with four of the same. What am I?", "A queue"),
    ("You'll find me in all of South but in none of East, West. What am I?", "The letter U"),
    ("You'll find me in all of Mars but in none of Venus. What am I?", "The letter R"),
    ("What goes up but never comes down?", "Your age"),
    ("What kind of band stretches without playing a note?", "A rubber band"),
    ("What gets bigger the more you take away from it?", "A hole"),
    ("What type of tree grows in your wallet?", "A palm (hand)"),
    ("You'll find me in all of Monday but in none of Sunday, Thursday. What am I?", "The letter M"),
    ("You'll find me in all of October but in none of February, March. What am I?", "The letter O"),
    ("You'll find me in all of Sunday but in none of Monday, Wednesday. What am I?", "The letter U"),
    ("You'll find me in all of North but in none of West, East. What am I?", "The letter N"),
    ("What can fill a whole room without taking any space?", "Light"),
    ("You'll find me in all of Saturday but in none of Tuesday. What am I?", "The letter R"),
    ("What kind of table is eaten?", "A vegetable"),
    ("The more you have of me, the less you see. What am I?", "Darkness"),
    ("I help you recall a secret without stating it. What am I?", "A password hint"),
    ("You'll find me in all of Friday but in none of Sunday. What am I?", "The letter R"),
    ("You'll find me in all of Jupiter, Mars, Earth, Mercury but in none of Venus. What am I?", "The letter R"),
    ("I circle the world without wings. What am I?", "A satellite"),
    ("What's the capital of a city without a map? (Trick)", "The first letter of the city's name"),
    ("I have teeth that open and close but never eat. What am I?", "A zipper"),
    ("You'll find me in all of Sunday but in none of Monday. What am I?", "The letter U"),
    ("You'll find me in all of December but in none of March, February. What am I?", "The letter D"),
    ("What line marks the end of your property but never writes?", "A fence"),
    ("You'll find me in all of Winter but in none of Summer, Autumn. What am I?", "The letter I"),
    ("You'll find me in all of Gold, Iron but in none of Lead, Tin. What am I?", "The letter O"),
    ("You'll find me in all of Spring but in none of Autumn. What am I?", "The letter G"),
    ("You'll find me in all of Gold but in none of Lead. What am I?", "The letter G"),
    ("What has a head, no neck; has a body, no legs; is brown or white; and is easy to crack?", "An egg"),
    ("You'll find me in all of Green, Red but in none of Black, Pink. What am I?", "The letter E"),
    ("I step without walking. What am I?", "A staircase"),
    ("You'll find me in all of December but in none of March. What am I?", "The letter D"),
    ("What has lanes but no seas?", "A road"),
    ("You'll find me in all of Red but in none of Black, Brown. What am I?", "The letter E"),
    ("What has 88 keys but can't open a single door?", "A piano"),
    ("You'll find me in all of November but in none of March, February. What am I?", "The letter O"),
    ("What five-letter word becomes shorter by adding two letters?", "Short"),
    ("What has many pages but cannot turn one?", "A book"),
    ("You'll find me in all of Iron, Gold but in none of Tin. What am I?", "The letter O"),
    ("What dances only when the wind plays music?", "A kite"),
    ("You'll find me in all of Sunday, Saturday but in none of Friday, Wednesday. What am I?", "The letter U"),
    ("I appear at night without being called and vanish at dawn without being stolen. What am I?", "A star"),
    ("What has a tail and a head but no body and is shiny?", "A coin"),
    ("You'll find me in all of Friday but in none of Wednesday, Saturday. What am I?", "The letter F"),
    ("What has a heart that doesn't beat and leaves that don't read?", "An artichoke"),
    ("You'll find me in all of Monday but in none of Wednesday, Thursday, Tuesday. What am I?", "The letter M"),
    ("What writes constellations across the night?", "A star"),
    ("You'll find me in all of Winter but in none of Autumn, Summer. What am I?", "The letter I"),
    ("You'll find me in all of Monday but in none of Saturday, Wednesday, Sunday, Thursday. What am I?", "The letter O"),
    ("You'll find me in all of November, October but in none of March, January. What am I?", "The letter B"),
    ("You'll find me in all of March but in none of May. What am I?", "The letter H"),
    ("The more you take, the more of me you leave. What am I?", "A footprint"),
    ("You can see me, but you cannot touch me; I copy your shape. What am I?", "A shadow"),
    ("You'll find me in all of Red, Green but in none of Black, Brown, Pink. What am I?", "The letter E"),
    ("You'll find me in all of Red but in none of Pink, Brown, Black. What am I?", "The letter E"),
    ("I have keys for letters, not for doors. What am I?", "A keyboard"),
    ("What kind of tree do you carry in your hand?", "A palm"),
    ("What tugs at a string from the sky?", "A kite"),
    ("You'll find me in all of Monday but in none of Thursday. What am I?", "The letter M"),
    ("What can travel around the sun and never get hot?", "A shadow (on a sundial)"),
    ("You'll find me in all of Friday but in none of Saturday, Wednesday, Tuesday. What am I?", "The letter I"),
    ("You'll find me in all of Green, Red but in none of Pink, Black, Brown. What am I?", "The letter E"),
    ("You'll find me in all of Silver but in none of Lead. What am I?", "The letter S"),
    ("What can't tell you who you are, only how you look?", "A mirror"),
    ("I fly without wings and cry without eyes. What am I?", "A cloud"),
    ("What animal needs to wear a wig?", "A bald eagle"),
    ("What two words, when combined, hold the most letters?", "Post office"),
    ("I measure without moving and draw lines without ink. What am I?", "A ruler"),
    ("I speak without a mouth and hear without ears. What am I?", "An echo"),
    ("I hide the sun and paint the sky. What am I?", "A cloud"),
    ("You'll find me in all of November, December but in none of March. What am I?", "The letter E"),
    ("You'll find me in all of March, April but in none of May, June. What am I?", "The letter R"),
    ("You'll find me in all of Monday but in none of Tuesday, Sunday, Saturday. What am I?", "The letter O"),
    ("Where do letters live before words are born?", "A keyboard"),
    ("You'll find me in all of Earth but in none of Venus. What am I?", "The letter H"),
    ("Smile at me and I smile back; frown, I frown. What am I?", "A mirror"),
    ("You'll find me in all of Sunday but in none of Monday, Friday. What am I?", "The letter U"),
    ("You'll find me in all of March, April but in none of May. What am I?", "The letter R"),
    ("You'll find me in all of North, South but in none of West. What am I?", "The letter H"),
    ("What gives light but fears the gust?", "A candle"),
    ("You'll find me in all of Red, Green but in none of Brown, Pink. What am I?", "The letter E"),
    ("What has four legs, offers a rest, but never walks?", "A chair"),
    ("What kind of dog tells time?", "A watch-dog"),
    ("What kind of ship sails on friendship alone?", "A relationship"),
    ("What can you hold only when you don't hold it?", "Your breath"),
    ("You'll find me in all of Spring, Winter but in none of Summer. What am I?", "The letter I"),
    ("You'll find me in all of Green but in none of Black, Brown, Pink. What am I?", "The letter G"),
    ("You'll find me in all of April, March but in none of May, June. What am I?", "The letter R"),
    ("You'll find me in all of South, North but in none of West. What am I?", "The letter H"),
    ("You'll find me in all of Red but in none of Brown, Pink. What am I?", "The letter E"),
    ("I hold many letters but cannot read. What am I?", "A mailbox"),
    ("You'll find me in all of Jupiter but in none of Neptune. What am I?", "The letter J"),
    ("You'll find me in all of December, November, October but in none of March. What am I?", "The letter B"),
    ("You'll find me in all of November but in none of February, January, March. What am I?", "The letter O"),
    ("I sleep in the soil but wake as a plant. What am I?", "A seed"),
    ("I am invisible but can move mountains. What am I?", "A thought"),
    ("You'll find me in all of October, November, December but in none of January. What am I?", "The letter B"),
    ("What has a bed that's made by a current and a mouth that never speaks?", "A river"),
    ("What can be cracked but never held, and made but never seen?", "A smile"),
    ("I go up and down stairs without moving. What am I?", "A carpet"),
    ("You'll find me in all of March, April but in none of June. What am I?", "The letter R"),
    ("What's full of news but never speaks?", "A newspaper"),
    ("You'll find me in all of November, December, October but in none of March. What am I?", "The letter B"),
    ("What stretches tall in the evening and shrinks at noon?", "A shadow"),
    ("You'll find me in all of Monday but in none of Sunday, Saturday, Wednesday. What am I?", "The letter O"),
    ("I leave a trail wherever I go and grow shorter with use. What am I?", "A pencil"),
    ("You'll find me in all of Jupiter but in none of Uranus, Venus, Saturn. What am I?", "The letter I"),
    ("What wears a snow cap and never feels cold?", "A mountain"),
    ("You'll find me in all of Saturday, Sunday but in none of Monday, Friday. What am I?", "The letter S"),
    ("If you have me, you want to share me; if you share me, you haven't got me. What am I?", "A secret"),
    ("What has rows of little teeth that never chew?", "A zipper"),
    ("What divides neighbors but keeps no secrets?", "A fence"),
    ("I have teeth but never bite. What am I?", "A comb"),
    ("I dance with the wind but fear the rain. What am I?", "A kite"),
    ("You'll find me in all of North, South but in none of East. What am I?", "The letter H"),
    ("You'll find me in all of April but in none of June, May. What am I?", "The letter L"),
    ("You'll find me in all of Green but in none of Brown, Pink, Black. What am I?", "The letter G"),
    ("What's full of words yet stays quiet on the shelf?", "A book"),
    ("What can go up a chimney down, but not down a chimney up?", "An umbrella"),
    ("You'll find me in all of Winter, Spring but in none of Summer, Autumn. What am I?", "The letter I"),
    ("What kind of cup is best eaten?", "A cupcake"),
    ("What comes once in a minute, twice in a moment, and never in a century?", "The letter M"),
    ("I have bristles but not a beard. What am I?", "A toothbrush"),
    ("You'll find me in all of Saturday but in none of Monday, Tuesday, Wednesday. What am I?", "The letter R"),
    ("You'll find me in all of Monday but in none of Thursday, Tuesday, Sunday, Saturday. What am I?", "The letter O"),
    ("You'll find me in all of Friday but in none of Tuesday. What am I?", "The letter I"),
    ("You'll find me in all of November, October but in none of February, January. What am I?", "The letter O"),
    ("What's a home for bats and echoes?", "A cave"),
    ("You'll find me in all of Mars, Mercury but in none of Venus, Uranus, Neptune, Saturn. What am I?", "The letter M"),
    ("What dreams of trees inside a shell?", "A seed"),
    ("What ticks but has no heartbeat?", "A clock"),
    ("What kind of room can you eat?", "A mushroom"),
    ("You'll find me in all of Jupiter, Mars but in none of Venus. What am I?", "The letter R"),
    ("What spins in circles but has no legs?", "A coin"),
    ("You'll find me in all of Tiger, Zebra, Giraffe but in none of Lion. What am I?", "The letter R"),
    ("You'll find me in all of December, November but in none of January, February. What am I?", "The letter M"),
    ("I add to any room but take up no space. What am I?", "Light"),
    ("You'll find me in all of Red but in none of Pink. What am I?", "The letter D"),
    ("What bristles with purpose at dawn and night?", "A toothbrush"),
    ("You'll find me in all of Giraffe, Zebra, Tiger but in none of Lion. What am I?", "The letter R"),
    ("You'll find me in all of Winter but in none of Autumn. What am I?", "The letter I"),
    ("What's a vampire's favorite fruit?", "A blood orange"),
    ("Seven is odd; remove one letter and I become even. What word am I?", "Seven"),
    ("What has many stories but can't tell one?", "A library"),
    ("You'll find me in all of Mercury, Mars but in none of Uranus. What am I?", "The letter M"),
    ("What has a lens to see but no brain to think?", "A camera"),
    ("What's full of holes but still holds noodles?", "A colander"),
    ("You'll find me in all of Silver, Iron but in none of Lead, Tin. What am I?", "The letter R"),
    ("What has many rings but no fingers?", "A tree"),
    ("What connects places without moving an inch?", "A road"),
    ("What falls in winter but never gets hurt?", "Snow"),
    ("You'll find me in all of Green but in none of Brown, Pink. What am I?", "The letter G"),
    ("I have squares and numbers but no math problems. What am I?", "A calendar"),
    ("What runs but has no finish line and always wins?", "Time"),
    ("What loses time when its hands stop moving?", "A clock"),
    ("You'll find me in all of October but in none of January, February, March. What am I?", "The letter O"),
    ("You'll find me in all of Mars, Jupiter but in none of Venus. What am I?", "The letter R"),
    ("You'll find me in all of October, December but in none of March. What am I?", "The letter E"),
    ("What has a spine but no bones?", "A book"),
    ("You'll find me in all of Tiger but in none of Bear. What am I?", "The letter G"),
    ("I'm a seed you can read. What am I?", "A book"),
    ("What's a tree's favorite drink?", "Root beer"),
    ("I have degrees but never went to school. What am I?", "A thermometer"),
    ("You'll find me in all of Spring, Winter but in none of Autumn. What am I?", "The letter I"),
    ("You'll find me in all of December but in none of February, January. What am I?", "The letter C"),
    ("What can be cracked, written, told, and made but is not an egg?", "A joke"),
    ("What has a trunk but no wheels?", "A tree"),
    ("You'll find me in all of Mercury but in none of Neptune, Uranus, Venus. What am I?", "The letter C"),
    ("You'll find me in all of Friday but in none of Sunday, Tuesday. What am I?", "The letter F"),
    ("I can be heard but not held, quiet but powerful. What am I?", "A whisper"),
    ("What belongs to you but is used by others more than you?", "Your name"),
    ("What has many posts but never mails a letter?", "A fence"),
    ("What runs all day to keep cool?", "A refrigerator"),
    ("What reflects but never remembers?", "A mirror"),
    ("You'll find me in all of Earth but in none of Venus, Neptune, Saturn, Uranus. What am I?", "The letter H"),
    ("You'll find me in all of Saturday, Sunday but in none of Wednesday. What am I?", "The letter U"),
    ("What glitters though made of fire?", "A star"),
    ("What hears the ocean's heartbeat with no ears?", "A submarine"),
    ("What can jump higher than a house?", "Anything that can jump; houses can't"),
    ("What has a mouth but never speaks?", "A river"),
    ("You'll find me in all of Red, Green but in none of Black, Pink. What am I?", "The letter R"),
    ("What kind of room is smallest in a house of mushrooms?", "A mushroom"),
    ("What gets wetter the more it dries?", "A towel"),
    ("You'll find me in all of Monday but in none of Saturday, Wednesday. What am I?", "The letter M"),
    ("I rise when it's hot and fall when it's cold. What am I?", "A thermometer"),
    ("You'll find me in all of Zebra, Giraffe, Tiger but in none of Lion. What am I?", "The letter R"),
    ("What invention lets you look right through a wall?", "A window"),
    ("You'll find me in all of Monday but in none of Wednesday, Sunday, Thursday. What am I?", "The letter O"),
    ("What can travel around a house but never steps inside?", "A fence"),
    ("You'll find me in all of October, November but in none of March, February. What am I?", "The letter O"),
    ("What copies you yet disappears in the dark?", "A shadow"),
    ("You'll find me in all of Iron but in none of Lead, Tin. What am I?", "The letter R"),
    ("You'll find me in all of Tiger, Giraffe but in none of Bear, Lion. What am I?", "The letter G"),
    ("What has a ring but no finger and cries out when you need it?", "A telephone"),
    ("I always know North but have no brain. What am I?", "A compass"),
    ("You'll find me in all of North but in none of East. What am I?", "The letter H"),
    ("What fits like a second skin and waves without a hand?", "A glove"),
    ("You'll find me in all of Gold, Silver but in none of Tin. What am I?", "The letter L"),
    ("I am not a river but I have banks; not a tree but I have leaves; not a man but I have a spine. What am I?", "A book"),
    ("You'll find me in all of Winter, Spring but in none of Summer. What am I?", "The letter N"),
    ("You'll find me in all of Monday but in none of Saturday. What am I?", "The letter N"),
    ("You'll find me in all of Earth but in none of Uranus, Neptune, Saturn. What am I?", "The letter H"),
    ("You'll find me in all of Green, Red but in none of Pink. What am I?", "The letter R"),
    ("You'll find me in all of Silver but in none of Tin. What am I?", "The letter E"),
    ("I twinkle far away but burn like a sun up close. What am I?", "A star"),
    ("What has bark but never bites?", "A tree"),
    ("You'll find me in all of Red but in none of Black, Pink. What am I?", "The letter D"),
    ("You'll find me in all of Zebra but in none of Lion, Bear. What am I?", "The letter Z"),
    ("You'll find me in all of North, South but in none of West, East. What am I?", "The letter H"),
    ("You'll find me in all of South, North but in none of East, West. What am I?", "The letter O"),
    ("You'll find me in all of Tiger but in none of Bear, Lion. What am I?", "The letter G"),
    ("I have lakes with no water, mountains with no stone, and cities with no people. What am I?", "A map"),
    ("You'll find me in all of April, March but in none of June. What am I?", "The letter R"),
    ("You'll find me in all of Winter, Spring but in none of Autumn, Summer. What am I?", "The letter I"),
    ("I can be long or I can be short; I can be grown or I can be bought; I can be painted or left bare; round or square, I do not care. What am I?", "A fingernail"),
    ("I'm always hungry and must be fed; the finger I touch will soon turn red. What am I?", "Fire"),
    ("You'll find me in all of Friday but in none of Thursday, Tuesday, Sunday, Wednesday, Saturday. What am I?", "The letter I"),
    ("You'll find me in all of Sunday but in none of Thursday, Friday, Tuesday. What am I?", "The letter N"),
    ("You'll find me in all of Monday but in none of Wednesday, Saturday, Sunday. What am I?", "The letter M"),
    ("What kind of key opens a banana?", "A monkey"),
    ("You'll find me in all of December but in none of January, February, March. What am I?", "The letter D"),
    ("You'll find me in all of Zebra, Giraffe but in none of Lion. What am I?", "The letter R"),
    ("What goes up when the rain comes down?", "An umbrella"),
    ("What has a lot of horns but never honks?", "A herd of cattle"),
    ("What soaks up a lot and gives it all back?", "A towel"),
    ("I'm unique and short-lived, born from cold breath. What am I?", "A snowflake"),
    ("You'll find me in all of Silver, Iron but in none of Lead. What am I?", "The letter R"),
    ("You'll find me in all of Green but in none of Pink. What am I?", "The letter G"),
    ("What has ears all over the field but hears nothing at all?", "Corn"),
    ("You'll find me in all of Friday but in none of Sunday, Tuesday, Saturday, Wednesday. What am I?", "The letter F"),
    ("I guard your door but live in your head. What am I?", "A password"),
    ("You'll find me in all of Green, Red but in none of Black, Brown, Pink. What am I?", "The letter E"),
    ("You pass the runner in second just before the tape—what place do you take?", "Second place"),
    ("You'll find me in all of Friday but in none of Saturday, Thursday. What am I?", "The letter F"),
    ("You'll find me in all of Friday but in none of Wednesday, Tuesday, Sunday, Saturday, Thursday. What am I?", "The letter F"),
    ("What comes down but never goes up?", "Rain"),
    ("Tiny as dust, I can become a forest. What am I?", "A seed"),
    ("You'll find me in all of Silver, Iron but in none of Tin. What am I?", "The letter R"),
    ("What reaches the clouds without growing leaves?", "A mountain"),
    ("You'll find me in all of December but in none of January, March, February. What am I?", "The letter D"),
    ("You'll find me in all of Green but in none of Brown, Black, Pink. What am I?", "The letter E"),
    ("What runs through towns and fields but never moves?", "A road"),
    ("What can be filled to the brim without holding a drop?", "A schedule"),
    ("You'll find me in all of Monday but in none of Sunday, Saturday, Wednesday, Tuesday, Thursday. What am I?", "The letter M"),
    ("What has many needles but doesn't sew?", "A Christmas tree"),
    ("You'll find me in all of Friday but in none of Sunday, Thursday, Wednesday, Tuesday. What am I?", "The letter I"),
    ("You'll find me in all of Saturday but in none of Wednesday, Monday, Tuesday. What am I?", "The letter R"),
    ("I have keys for songs, not for locks. What am I?", "A piano"),
    ("What carves canyons without tools?", "A river"),
    ("What building has the most stories?", "The library"),
    ("You'll find me in all of Mercury, Earth but in none of Uranus. What am I?", "The letter E"),
    ("You'll find me in all of Sunday but in none of Tuesday, Friday. What am I?", "The letter N"),
    ("What sings when wind runs through it?", "A whistle"),
    ("What wears green in summer and none in winter?", "A tree"),
    ("You'll find me in all of Green, Red but in none of Black, Brown. What am I?", "The letter E"),
    ("You'll find me in all of October but in none of February, March, January. What am I?", "The letter T"),
    ("Turn me on my side and I am everything; cut me in half and I am nothing. What number am I?", "8"),
    ("I start with T, end with T, and am filled with T, but I'm not a teapot. I'm…", "A teapot"),
    ("What has branches and customers but no fruit or leaves?", "A bank"),
    ("You'll find me in all of March but in none of June, May. What am I?", "The letter H"),
    ("What increases every birthday but never decreases?", "Your age"),
    ("You'll find me in all of Friday but in none of Sunday, Saturday. What am I?", "The letter F"),
    ("You'll find me in all of Winter but in none of Summer. What am I?", "The letter N"),
    ("You'll find me in all of December but in none of February, January, March. What am I?", "The letter D"),
    ("I see with sonar, not eyes. What am I?", "A submarine"),
    ("I fly while tied down. What am I?", "A kite"),
    ("What has a tongue that never tastes and soles that never sleep?", "A shoe"),
    ("You'll find me in all of Red, Green but in none of Pink, Brown. What am I?", "The letter E"),
    ("What is unique, silent, and cold?", "A snowflake"),
    ("What flows to the sea but never walks a step?", "A river"),
    ("You'll find me in all of Sunday but in none of Monday, Friday, Wednesday. What am I?", "The letter U"),
    ("What runs but has no legs, whirls but has no hair, and roars without a mouth?", "The wind"),
    ("What can be opened but never closed?", "An egg"),
    ("What has many pages but never turns one by itself?", "A book"),
    ("What goes through cities and fields but never moves?", "A road"),
    ("You'll find me in all of Friday but in none of Tuesday, Thursday, Sunday. What am I?", "The letter F"),
    ("You'll find me in all of Friday but in none of Wednesday, Tuesday, Saturday, Sunday, Thursday. What am I?", "The letter I"),
    ("What can you hold after it's given to you and still keep it when it's gone?", "A memory"),
    ("You'll find me in all of October but in none of February. What am I?", "The letter O"),
    ("You'll find me in all of Saturday, Sunday but in none of Wednesday, Monday. What am I?", "The letter U"),
    ("You'll find me in all of Jupiter but in none of Uranus. What am I?", "The letter E"),
    ("You'll find me in all of Green but in none of Pink, Black, Brown. What am I?", "The letter G"),
    ("You'll find me in all of Mercury but in none of Saturn, Venus. What am I?", "The letter Y"),
    ("You'll find me in all of Red, Green but in none of Pink. What am I?", "The letter E"),
    ("Shout and I answer, whisper and I fade. What am I?", "An echo"),
    ("You'll find me in all of Friday but in none of Tuesday, Wednesday, Sunday, Saturday, Thursday. What am I?", "The letter F"),
    ("What always points at the future but counts the past?", "A clock"),
    ("What do others call out that belongs to you?", "A name"),
    ("What fights plaque twice a day?", "A toothbrush"),
    ("What sort of line is full of people and letters?", "A queue"),
    ("What has one eye but can still see nothing and is used to guide thread?", "A needle"),
    ("You'll find me in all of Spring, Winter but in none of Autumn, Summer. What am I?", "The letter I"),
    ("You'll find me in all of Green but in none of Brown, Black. What am I?", "The letter G"),
    ("I visit in sleep and fade at dawn. What am I?", "A dream"),
    ("You'll find me in all of Friday but in none of Thursday. What am I?", "The letter I"),
    ("You'll find me in all of South but in none of East. What am I?", "The letter U"),
    ("You'll find me in all of Giraffe, Zebra but in none of Lion. What am I?", "The letter E"),
    ("You'll find me in all of Tiger, Giraffe but in none of Lion. What am I?", "The letter G"),
    ("You'll find me in all of Giraffe, Tiger but in none of Bear. What am I?", "The letter I"),
    ("You'll find me in all of April, March but in none of May. What am I?", "The letter R"),
    ("What has a bed but never sleeps?", "A river"),
    ("What has hands that wave but never wash?", "A clock"),
    ("I'm tall when I'm young and short when I'm old. What am I?", "A candle"),
    ("You'll find me in all of Mars but in none of Saturn, Neptune, Uranus. What am I?", "The letter M"),
    ("What has two banks and a current between?", "A bank (river)"),
    ("What guides ships by standing still?", "A lighthouse"),
    ("What has a head and a tail but no body?", "A coin"),
    ("What has bark but never bites and wears leaves like clothes?", "A tree"),
    ("I change every month no matter what. What am I?", "A calendar"),
    ("You'll find me in all of Silver but in none of Tin, Lead. What am I?", "The letter R"),
    ("What lets you type thoughts into light?", "A keyboard"),
    ("You'll find me in all of April but in none of June. What am I?", "The letter L"),
    ("You'll find me in all of Iron, Gold but in none of Lead. What am I?", "The letter O"),
    ("What calls players to start and stop?", "A whistle"),
    ("I eat air and fear the rain. What am I?", "A candle"),
    ("What makes thunder's drum without sticks?", "A cloud"),
    ("You'll find me in all of Winter, Spring but in none of Autumn. What am I?", "The letter I"),
    ("You'll find me in all of October, December, November but in none of January, March. What am I?", "The letter B"),
    ("What is small enough to hide in a pocket but big enough to become a forest?", "A seed"),
    ("I'm a word of letters three; add two and fewer there will be. What word am I?", "Few"),
    ("You'll find me in all of Friday but in none of Tuesday, Thursday, Wednesday, Saturday, Sunday. What am I?", "The letter F"),
    ("I have wheels and flies, but I'm not a plane. What am I?", "A garbage truck"),
    ("You'll find me in all of December, October but in none of February. What am I?", "The letter C"),
    ("You'll find me in all of Green, Red but in none of Black, Pink, Brown. What am I?", "The letter E"),
    ("Take me out of a window and I'll leave a grievous hole; put me in a door and I'll make it whole. What am I?", "A letter D"),
    ("You'll find me in all of North but in none of East, West. What am I?", "The letter R"),
    ("You'll find me in all of Gold but in none of Tin, Lead. What am I?", "The letter O"),
    ("What shows truth reversed?", "A mirror"),
    ("Where are roads and routes drawn but nothing moves?", "A map"),
    ("You'll find me in all of South, North but in none of East. What am I?", "The letter H"),
    ("What has a title but never wears a crown?", "A book"),
    ("I shoot without bullets and develop memories. What am I?", "A camera"),
    ("I am hollow yet full of stone. What am I?", "A cave"),
    ("What must be broken before it can be used, besides an egg?", "A glow stick"),
    ("I'm a line that moves slowly and grows fast. What am I?", "A queue"),
    ("You'll find me in all of Green, Red but in none of Brown, Black. What am I?", "The letter E"),
    ("You'll find me in all of Spring, Winter but in none of Summer, Autumn. What am I?", "The letter I"),
    ("What stands in one place but leaves every year?", "A tree"),
    ("What's a ghost's favorite dessert?", "I scream (ice cream)"),
    ("I go up when the rain comes down. What am I?", "An umbrella"),
    ("What can write a future and erase a past?", "A pencil"),
    ("What music are balloons afraid of?", "Pop"),
    ("I keep things cold but fear the door left open. What am I?", "A refrigerator"),
    ("You'll find me in all of October but in none of February, January. What am I?", "The letter C"),
    ("What has a neck but no head?", "A bottle"),
    ("You'll find me in all of South, North but in none of West, East. What am I?", "The letter H"),
    ("What has a head of lettuce and a crown of leaves, yet no brain?", "Lettuce"),
    ("What gets sharper the more you use it?", "Your brain"),
    ("You'll find me in all of Gold, Iron but in none of Lead. What am I?", "The letter O"),
    ("Which object bristles with teeth yet takes no lunch?", "A comb"),
    ("You'll find me in all of Green, Red but in none of Pink, Black. What am I?", "The letter E"),
    ("I jog your memory but tell nothing. What am I?", "A password hint"),
    ("You'll find me in all of Green but in none of Black. What am I?", "The letter N"),
    ("You'll find me in all of Red, Green but in none of Pink, Black, Brown. What am I?", "The letter E"),
    ("You'll find me in all of Saturday, Sunday but in none of Friday, Wednesday. What am I?", "The letter U"),
    ("What has a flag that isn't a country?", "A mailbox"),
    ("You'll find me in all of March but in none of June. What am I?", "The letter A"),
    ("What has streets but no cars, and lights but no stars?", "A map"),
    ("I fight plaque without a sword. What am I?", "A toothbrush"),
    ("What flies forever, rests never, and is never seen?", "Time"),
    ("You'll find me in all of Monday but in none of Thursday, Tuesday, Saturday. What am I?", "The letter N"),
    ("You'll find me in all of Spring but in none of Summer. What am I?", "The letter P"),
    ("You'll find me in all of Giraffe, Tiger but in none of Lion. What am I?", "The letter E"),
    ("What has an eye on a thread, yet cannot see?", "A needle"),
    ("You'll find me in all of October but in none of January. What am I?", "The letter B"),
    ("I have cities without houses and rivers without water. What am I?", "A map"),
    ("You'll find me in all of Green but in none of Brown. What am I?", "The letter E"),
    ("I start fires by losing my head. What am I?", "A match"),
    ("You'll find me in all of Saturday, Sunday but in none of Monday. What am I?", "The letter S"),
    ("I relay voices across the sky. What am I?", "A satellite"),
    ("I'm measured in hours and feed on air; thin I'm fast, fat I'm slow. What am I?", "A candle"),
    ("I dive deep but am not a fish. What am I?", "A submarine"),
    ("What has lanes but no waves?", "A road"),
    ("What travels the world and never sees the sun?", "A submarine"),
    ("I point the way but never move. What am I?", "A compass"),
    ("You'll find me in all of December but in none of February, March. What am I?", "The letter D"),
    ("What runs but never walks?", "A river"),
    ("What has four wheels and flies?", "A garbage truck (full of 'flies')"),
    ("What dies if it drinks and lives while it eats air?", "A candle"),
    ("I make a sound without a tongue. What am I?", "A whistle"),
    ("What shines for others and sleeps by day?", "A lighthouse"),
    ("You'll find me in all of Iron but in none of Tin, Lead. What am I?", "The letter R"),
    ("What kind of room is outside and grows on a lawn?", "A mushroom"),
    ("You'll find me in all of November but in none of March, February, January. What am I?", "The letter O"),
    ("You'll find me in all of October but in none of March. What am I?", "The letter B"),
    ("What has many teeth and a long zipper smile but never bites?", "A zipper"),
    ("What's a scarecrow's favorite fruit?", "Straw-berries"),
    ("You'll find me in all of October, December but in none of February. What am I?", "The letter C"),
    ("What net is spun without rope?", "A web"),
    ("You'll find me in all of Red but in none of Black, Brown, Pink. What am I?", "The letter D"),
    ("You'll find me in all of Spring but in none of Summer, Autumn. What am I?", "The letter I"),
    ("What has a face but no eyes?", "A clock"),
    ("You'll find me in all of Earth but in none of Neptune, Venus, Saturn. What am I?", "The letter H"),
    ("What is born in clouds and dies on your tongue?", "A snowflake"),
    ("You'll find me in all of Iron, Silver but in none of Lead, Tin. What am I?", "The letter R"),
    ("You'll find me in all of North but in none of West. What am I?", "The letter H"),
    ("You'll find me in all of Giraffe but in none of Bear, Lion. What am I?", "The letter G"),
    ("Which thing shows its teeth only to keep things together?", "A zipper"),
    ("You'll find me in all of March, April but in none of June, May. What am I?", "The letter R"),
    ("I'm not alive, but I can bloom in the sky after rain. What am I?", "A rainbow"),
    ("You'll find me in all of Red, Green but in none of Brown. What am I?", "The letter E"),
    ("You'll find me in all of Friday but in none of Tuesday, Saturday, Wednesday, Sunday, Thursday. What am I?", "The letter F"),
    ("What is full of holes but still holds water?", "A sponge"),
    ("What has hands but cannot clap?", "A clock"),
    ("What gets taken before you get it?", "A photograph"),
    ("What runs, never tires; murmurs, never talks; has a bed, never sleeps?", "A river"),
    ("What has a neck but no head and is filled to be useful?", "A bottle"),
    ("You'll find me in all of Mars, Mercury but in none of Uranus, Saturn, Venus. What am I?", "The letter M"),
    ("You'll find me in all of Red, Green but in none of Black. What am I?", "The letter R"),
    ("What kind of key has legs and hops?", "A turkey"),
    ("You'll find me in all of April, March but in none of June, May. What am I?", "The letter R"),
    ("What speaks without a voice and is heard with your eyes?", "A book"),
    ("What keeps cool even in summer and repeats what you say?", "A cave"),
    ("You'll find me in all of South but in none of West. What am I?", "The letter U"),
    ("What has keys you can't eat, and lettuce you can't read?", "A keyboard"),
    ("You'll find me in all of Giraffe but in none of Lion, Bear. What am I?", "The letter G"),
    ("What has one head, four fingers and a thumb, but is not alive?", "A glove"),
    ("What has four fingers and a thumb but isn't alive?", "A glove"),
    ("What is yours but used by others more?", "A name"),
    ("What types without fingers and sings with clicks?", "A keyboard"),
    ("You'll find me in all of Tiger, Zebra but in none of Lion. What am I?", "The letter R"),
    ("What has roots that nobody sees and is taller than trees?", "A mountain"),
    ("What has a ring that you cannot wear and a number that you can dial?", "A telephone"),
    ("You'll find me in all of Red but in none of Black, Pink, Brown. What am I?", "The letter E"),
]

def add_riddles_to_db(new_riddles_data):
    """Add new riddles to the database with comprehensive duplicate checking"""

    print("Checking for duplicates within the new riddle batch...")
    batch_duplicates = find_duplicates_in_batch(new_riddles_data)

    if batch_duplicates:
        print(f"WARNING: Found {len(batch_duplicates)} potential duplicates in batch:")
        for i, j, dup_type, text in batch_duplicates[:10]:
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
    processed_questions = set()

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

if __name__ == "__main__":
    add_riddles_to_db(NEW_RIDDLES)