import sqlite3
import re

riddles_batch6 = [
    ("I turn cheese into tiny snow. What am I?", "A grater"),
    ("I'm a handle that opens opportunities. What am I?", "A doorknob"),
    ("Winds sculpt me into hills by the sea or in deserts. What am I?", "A sand dune"),
    ("Kids and grownups use me: a pipette. What am I?", "A pipette"),
    ("I help with tasks as a lanyard. What am I?", "A lanyard"),
    ("Kids and grownups use me: a compass case. What am I?", "A compass case"),
    ("I fly in a curve and return to where I started. Who am I?", "A boomerang"),
    ("Kids and grownups use me: a canteen. What am I?", "A canteen"),
    ("I circle Earth and carry calls and pictures. What am I?", "A satellite"),
    ("I turn and make endless patterns from bits of glass. What am I?", "A kaleidoscope"),
    ("I'm a roof that opens to the stars. What am I?", "A telescope dome"),
    ("Click me on and shadows run away. What am I?", "A flashlight"),
    ("I bloom in the sky and drift down. What am I?", "A parachute"),
    ("I span gaps so journeys continue. What am I?", "A bridge"),
    ("I make words crisp with edges. What am I?", "A consonant"),
    ("Speak into me and I'll carry your words. What am I?", "A microphone"),
    ("I guard ships by caring for a tall light. Who am I?", "A lighthouse keeper"),
    ("I help with tasks as graph paper. What am I?", "Graph paper"),
    ("I'm the artist of camouflage. What am I?", "A chameleon"),
    ("I keep time with a steady tick‑tock for music practice. What am I?", "A metronome"),
    ("I move so slowly that moss grows on me. What am I?", "A sloth"),
    ("I'm a pile of grains that walks with the wind. What am I?", "A sand dune"),
    ("Kids and grownups use me: trail markers. What am I?", "Trail markers"),
    ("Desert animals drink from me without a straw. What am I?", "A cactus"),
    ("Kids and grownups use me: a name tag. What am I?", "A name tag"),
    ("I'm a tiny arrow with a favorite direction. What am I?", "A magnet needle (compass)"),
    ("Lights shine inside me for drivers. What am I?", "A tunnel"),
    ("I'm loud but never seen. What am I?", "Thunder"),
    ("I go through a mountain so you don't have to go over. What am I?", "A tunnel"),
    ("Only the correct pattern of teeth can open me. What am I?", "A keyhole"),
    ("I watch the sea and keep the lamp burning. Who am I?", "A lighthouse keeper"),
    ("Germs and cells become giants in my glass. What am I?", "A microscope"),
    ("I have numbers and a spout for pouring. What am I?", "A beaker"),
    ("I wear old clothes and never move, yet I guard crops. What am I?", "A scarecrow"),
    ("Kids and grownups use me: a map legend. What am I?", "A map legend"),
    ("I rumble like giant drums. What am I?", "Thunder"),
    ("I can grow a new arm if I lose one. What am I?", "A starfish"),
    ("I help with tasks as elbow pads. What am I?", "Elbow pads"),
    ("I help with tasks as a lab coat. What am I?", "A lab coat"),
    ("Kids and grownups use me: curtains. What am I?", "Curtains"),
    ("Ships watch for my beam on dark nights. What am I?", "A lighthouse"),
    ("Kids and grownups use me: a keychain. What am I?", "A keychain"),
    ("Black squares hold my message. What am I?", "A QR code"),
    ("I help with tasks as kneepads. What am I?", "Kneepads"),
    ("Kids and grownups use me: a skateboard. What am I?", "A skateboard"),
    ("I help with tasks as curtains. What am I?", "Curtains"),
    ("Hang me up and I'll glow all around. What am I?", "A lantern"),
    ("I'm a fuzzy swimmer with a beaver tail and a bill. What am I?", "A platypus"),
    ("Kids and grownups use me: a sled. What am I?", "A sled"),
    ("Kids and grownups use me: graph paper. What am I?", "Graph paper"),
    ("I move so slowly you might not notice. What am I?", "A glacier"),
    ("A breeze makes my colors blur. What am I?", "A pinwheel"),
    ("I stand by the sea and sweep light across waves. What am I?", "A lighthouse"),
    ("I let you visit the moon without leaving home. What am I?", "A telescope"),
    ("I make headlights glow halos. What am I?", "Fog"),
    ("I help with tasks as a skate helmet. What am I?", "A skate helmet"),
    ("I help with tasks as a water bottle. What am I?", "A water bottle"),
    ("Kids and grownups use me: an umbrella stand. What am I?", "An umbrella stand"),
    ("North seeks south when I'm around. What am I?", "A magnet"),
    ("Point and press; I obey your thumb. What am I?", "A remote control"),
    ("I save water for long trips. What am I?", "A camel"),
    ("I announce visitors with a clang. What am I?", "A doorknocker"),
    ("I help with tasks as a coat rack. What am I?", "A coat rack"),
    ("Without me, doors would fall or refuse to move. What am I?", "A hinge"),
    ("Press my button to hear my loud voice. What am I?", "A smoke alarm"),
    ("I help with tasks as a sleeping bag. What am I?", "A sleeping bag"),
    ("Kids and grownups use me: a hiking boot. What am I?", "A hiking boot"),
    ("I help with tasks as a staple remover. What am I?", "A staple remover"),
    ("My wings beat faster than you can count. What am I?", "A hummingbird"),
    ("I'm the joint that helps doors swing. What am I?", "A hinge"),
    ("Wipe your shoes on me before you enter. What am I?", "A doormat"),
    ("I read the same forward and backward. What am I?", "A palindrome"),
    ("I pour stew by the scoop. What am I?", "A ladle"),
    ("I help with tasks as a map legend. What am I?", "A map legend"),
    ("Cookies and pies meet me before the oven. What am I?", "A rolling pin"),
    ("I help with tasks as a kite string. What am I?", "A kite string"),
    ("Symmetry and sparkle spin inside me. What am I?", "A kaleidoscope"),
    ("I'm the hand that knocks when guests visit. What am I?", "A doorknocker"),
    ("I help with tasks as a lunchbox. What am I?", "A lunchbox"),
    ("Fish hide in my colorful branches. What am I?", "Coral"),
    ("I undress potatoes and carrots. What am I?", "A peeler"),
    ("Waves pulse me along. What am I?", "A jellyfish"),
    ("I'm a raindrop that froze into a tiny stone. What am I?", "Hail"),
    ("I help with tasks as a thermos. What am I?", "A thermos"),
    ("Kids and grownups use me: a life jacket. What am I?", "A life jacket"),
    ("I'm the unicorn of the ocean. What am I?", "A narwhal"),
    ("I'm the dark twin of a bright scene. What am I?", "Silhouette"),
    ("My eyes look two ways at once. What am I?", "A chameleon"),
    ("I help with tasks as a scooter. What am I?", "A scooter"),
    ("Words need me to speak smoothly. What am I?", "A vowel"),
    ("I scream to wake you when danger is in the air. What am I?", "A smoke alarm"),
    ("I help with tasks as a pipette. What am I?", "A pipette"),
    ("Kids and grownups use me: test tubes. What am I?", "Test tubes"),
    ("I'm nature's busy engineer. What am I?", "A beaver"),
    ("You know my shape but not my details. What am I?", "Silhouette"),
    ("I'm a letter the mouth opens wide to say. What am I?", "A vowel"),
    ("I shine inside a shell. What am I?", "A pearl"),
    ("Skydivers trust me to land softly. What am I?", "A parachute"),
    ("I'm proof you were here without saying a word. What am I?", "A footprint"),
    ("I help with tasks as a whiteboard. What am I?", "A whiteboard"),
    ("A, E, I, O, U belong to my family. What am I?", "A vowel"),
    ("I attract some metals but ignore wood and glass. What am I?", "A magnet"),
    ("I'm a puzzle of paths with dead ends. What am I?", "A maze"),
    ("I listen to lungs without ears. What am I?", "A stethoscope"),
    ("Kids and grownups use me: a chalkboard eraser. What am I?", "A chalkboard eraser"),
    ("I'm paper you don't read—just see. What am I?", "Wallpaper"),
    ("I help with tasks as a keychain. What am I?", "A keychain"),
    ("I've got speakers for shoulders. What am I?", "A boombox"),
    ("Specimens lie on me for a closer look. What am I?", "A microscope slide"),
    ("I mark glasses with a secret pattern. What am I?", "A fingerprint"),
    ("Grab me and twist; I'll let you in. What am I?", "A doorknob"),
    ("I'm stripes that machines can read. What am I?", "A barcode"),
    ("I help with tasks as a stapler. What am I?", "A stapler"),
    ("Shake me and flour falls like dust. What am I?", "A sieve"),
    ("I help with tasks as ice skates. What am I?", "Ice skates"),
    ("I'm morning jewels on grass. What am I?", "Dew"),
    ("I'm a staircase that moves on my own. What am I?", "An escalator"),
    ("I help with tasks as a doorstop. What am I?", "A doorstop"),
    ("Kids and grownups use me: swim goggles. What am I?", "Swim goggles"),
    ("I tap the roof like thrown pebbles. What am I?", "Hail"),
    ("Kids and grownups use me: a sleeping bag. What am I?", "A sleeping bag"),
    ("I'm a tiny windmill on a stick. What am I?", "A pinwheel"),
    ("I wait for the sweep to deliver the mess. What am I?", "A dustpan"),
    ("I see through skin to bones beneath. What am I?", "An X‑ray"),
    ("I'm a floppy topper for a straw guardian. What am I?", "A scarecrow hat"),
    ("Kids and grownups use me: a lab coat. What am I?", "A lab coat"),
    ("I'm a box that blasts music loud. What am I?", "A boombox"),
    ("Kids and grownups use me: a campfire ring. What am I?", "A campfire ring"),
    ("Kids and grownups use me: a scooter. What am I?", "A scooter"),
    ("Before bulbs, I used to burn; now I shine with batteries. What am I?", "A lantern"),
    ("I let you see over walls or from underwater. What am I?", "A periscope"),
    ("Fold by fold, I make animals from sheets. What am I?", "Origami"),
    ("I'm a fish who looks like a tiny horse. What am I?", "A seahorse"),
    ("I'm a house that keeps water outside. What am I?", "A boathouse"),
    ("I help with tasks as marshmallow sticks. What am I?", "Marshmallow sticks"),
    ("I lay eggs, swim well, and have a duck bill. What am I?", "A platypus"),
    ("I look like water in the distance, but I'm only hot air. What am I?", "A mirage"),
    ("I'm a stick that carries fire to light the way. What am I?", "A flaming torch"),
    ("I like water more than dust. What am I?", "A mop"),
    ("I'm a cloud that comes down to the ground. What am I?", "Fog"),
    ("Lost? Watch where I point. What am I?", "A magnet needle (compass)"),
    ("Wheels roll onto me and off again. What am I?", "A ferry"),
    ("I'm a garage that floats by the shore. What am I?", "A boathouse"),
    ("Cartographers draw me to guide travelers. What am I?", "A compass rose"),
    ("Dads carry the babies with me. What am I?", "A seahorse"),
    ("Clouds pass over my glass ceiling. What am I?", "A skylight"),
    ("Kids and grownups use me: a snow globe. What am I?", "A snow globe"),
    ("I'm a tiny swirl that's yours alone. What am I?", "A fingerprint"),
    ("Submarines use me to look above the waves. What am I?", "A periscope"),
    ("I'm a see‑through umbrella that swims. What am I?", "A jellyfish"),
    ("Put a drop on me and science begins. What am I?", "A microscope slide"),
    ("Ships fear my unseen part. What am I?", "An iceberg"),
    ("I help with tasks as a snorkel. What am I?", "A snorkel"),
    ("I fly underwater instead of in the sky. What am I?", "A penguin"),
    ("Tilt or tap and I guide the game. What am I?", "A joystick"),
    ("I'm a window in the roof that brings down the day. What am I?", "A skylight"),
    ("I help with tasks as a wristwatch. What am I?", "A wristwatch"),
    ("I tell stories on a wall using hands and light. What am I?", "A shadow puppet"),
    ("I show walls before they exist. What am I?", "A blueprint"),
    ("I curl my tail to hold onto sea grass. What am I?", "A seahorse"),
    ("I paint windows with white lace on cold mornings. What am I?", "Frost"),
    ("I help with tasks as a sled. What am I?", "A sled"),
    ("Upside down is my favorite way to hang. What am I?", "A sloth"),
    ("I get my color from the food I eat. What am I?", "A flamingo"),
    ("I'm small and picky about which teeth I let in. What am I?", "A keyhole"),
    ("I have steps that never stop climbing. What am I?", "An escalator"),
    ("I cast a shadow big enough for cities. What am I?", "An eclipse"),
    ("I bite your nose and sparkle on grass. What am I?", "Frost"),
    ("I help with tasks as roller skates. What am I?", "Roller skates"),
    ("I beat without hands to fluff eggs and cream. What am I?", "A whisk"),
    ("I point with a shadow instead of a finger to mark the hour. What am I?", "A sundial"),
    ("I carve valleys as I slide. What am I?", "A glacier"),
    ("I'm the round thing you turn to enter. What am I?", "A doorknob"),
    ("Before doorbells, people lifted me to make a sound. What am I?", "A doorknocker"),
    ("Kids and grownups use me: a drawing compass. What am I?", "A drawing compass"),
    ("I help with tasks as a pocket watch. What am I?", "A pocket watch"),
    ("Kids and grownups use me: a whiteboard. What am I?", "A whiteboard"),
    ("I tell a scanner who I am without words. What am I?", "A barcode"),
    ("Witches ride me; cleaners guide me. What am I?", "A broom"),
    ("Bird‑watchers love me for my double view. What am I?", "Binoculars"),
    ("Kids and grownups use me: a bookmark. What am I?", "A bookmark"),
    ("I keep paints handy like a colorful plate. What am I?", "A palette"),
    ("Doctors check me to see how you feel. What am I?", "A thermometer"),
    ("I help with tasks as test tubes. What am I?", "Test tubes"),
    ("Clap me out in words like 'ba-na-na'. What am I?", "A syllable"),
    ("I'm a plan on paper for buildings not yet built. What am I?", "A blueprint"),
    ("I help with tasks as swim goggles. What am I?", "Swim goggles"),
    ("I'm a letter that adds shape and stops to words. What am I?", "A consonant"),
    ("I'm a net for tiny things in the kitchen. What am I?", "A sieve"),
    ("Drive around me to choose your exit. What am I?", "A roundabout"),
    ("Kids and grownups use me: a curtain rod. What am I?", "A curtain rod"),
    ("Pianists love my constant tempo. What am I?", "A metronome"),
    ("I spin to show the breeze's path. What am I?", "A weathervane"),
    ("Carry me to bring the party with you. What am I?", "A boombox"),
    ("Turn your fingers into animals to make me. What am I?", "A shadow puppet"),
    ("Kids and grownups use me: a typewriter. What am I?", "A typewriter"),
    ("I don't stab or scoop; I pinch your dinner. What am I?", "Chopsticks"),
    ("I'm a mammal who loves the sea. What am I?", "A dolphin"),
    ("I'm a theater made from silhouettes. What am I?", "A shadow puppet"),
    ("Architects read me like a map of a house. What am I?", "A blueprint"),
    ("I show moving pictures in your living room. What am I?", "A television"),
    ("I surf the waves and leap for fun. What am I?", "A dolphin"),
    ("I tell time without hands or numbers, guided by the sun's shadow. What am I?", "A sundial"),
    ("I grow from a cave ceiling, dripping over years. What am I?", "A stalactite"),
    ("Grain of sand in, jewel out—who am I?", "A pearl"),
    ("I pull without touching, but only certain things. What am I?", "A magnet"),
    ("People think I'm a bear, but I'm not. What am I?", "A koala"),
    ("I let the small through and keep the big. What am I?", "A sieve"),
    ("I'm a wire tornado in the kitchen. What am I?", "A whisk"),
    ("Kids and grownups use me: a toboggan. What am I?", "A toboggan"),
    ("I wash floors with a hair‑do of strings. What am I?", "A mop"),
    ("Swing my arm and the beat stays true. What am I?", "A metronome"),
    ("I help with tasks as a typewriter. What am I?", "A typewriter"),
    ("Storms can't blow out my signal. What am I?", "A lighthouse"),
    ("I have doors that open on different floors. What am I?", "An elevator"),
    ("I charge from cloud to ground in a flash. What am I?", "Lightning"),
    ("I'm a little tray that likes dirt. What am I?", "A dustpan"),
    ("Drips from above help me stand tall. What am I?", "A stalagmite"),
    ("I help with tasks as trail markers. What am I?", "Trail markers"),
    ("I point where the wind is going. What am I?", "A weathervane"),
    ("Kids and grownups use me: a clipboard. What am I?", "A clipboard"),
    ("I fall hard and bounce on the ground. What am I?", "Hail"),
    ("Crows don't like my stitched smile. What am I?", "A scarecrow"),
    ("I'm a boat that carries cars and people. What am I?", "A ferry"),
    ("I help with tasks as a nightlight. What am I?", "A nightlight"),
    ("I rise from the cave floor like a stone tooth. What am I?", "A stalagmite"),
    ("Kids and grownups use me: a music box. What am I?", "A music box"),
    ("Musicians use my steady tone to tune. What am I?", "A tuning fork"),
    ("Peel and stick, I change the room's look. What am I?", "Wallpaper"),
    ("I hide the world in a soft white blanket. What am I?", "Fog"),
    ("Kids and grownups use me: a coat rack. What am I?", "A coat rack"),
    ("Waves roll me smooth. What am I?", "A seashell"),
    ("Arctic waters are my home. What am I?", "A narwhal"),
    ("I'm the first to greet your feet at the door. What am I?", "A doormat"),
    ("I build reefs from tiny living stones. What am I?", "Coral"),
    ("Most of me hides under water. What am I?", "An iceberg"),
    ("I'm the wooden road inside your house. What am I?", "Floorboards"),
    ("Kids and grownups use me: ice skates. What am I?", "Ice skates"),
    ("Wear me to keep your music private. What am I?", "Headphones"),
    ("I leave wet trails that soon dry. What am I?", "A mop"),
    ("Kids and grownups use me: a lunchbox. What am I?", "A lunchbox"),
    ("I flatten dough into sheets without a press. What am I?", "A rolling pin"),
    ("A flick of me turns day into night and back again—indoors. What am I?", "A light switch"),
    ("I change my colors to blend in. What am I?", "A chameleon"),
    ("I'm a pocket‑sized beam of light. What am I?", "A flashlight"),
    ("I'm a bird who wears a tuxedo and swims. What am I?", "A penguin"),
    ("I orbit high to help with maps and weather. What am I?", "A satellite"),
    ("Detectives dust for me at scenes. What am I?", "A fingerprint"),
    ("I'm a mammal that breaks the rules. What am I?", "A platypus"),
    ("Turn my dial and stations change. What am I?", "A radio"),
    ("Kids and grownups use me: elbow pads. What am I?", "Elbow pads"),
    ("I'm a smart swimmer who talks in clicks and whistles. What am I?", "A dolphin"),
    ("I help with tasks as a skateboard. What am I?", "A skateboard"),
    ("Gamers grip me to fly and race on screens. What am I?", "A joystick"),
    ("I help with tasks as a hiking boot. What am I?", "A hiking boot"),
    ("Kids and grownups use me: kneepads. What am I?", "Kneepads"),
    ("Kids and grownups use me: a flashlight battery. What am I?", "A flashlight battery"),
    ("I sleep most of the day in Australian trees. What am I?", "A koala"),
    ("Put me to your ear to hear the ocean pretend. What am I?", "A seashell"),
    ("I hang from roofs after snowy days. What am I?", "An icicle"),
    ("I drum on trunks to send messages. What am I?", "A woodpecker"),
    ("I roll back at night so astronomers can peek. What am I?", "A telescope dome"),
    ("Two bulbs and a narrow neck, I count the moments grain by grain. What am I?", "An hourglass"),
    ("I help with tasks as a protractor. What am I?", "A protractor"),
    ("Kids and grownups use me: a stapler. What am I?", "A stapler"),
    ("I lift people without using stairs. What am I?", "An elevator"),
    ("Kids and grownups use me: a cuckoo clock. What am I?", "A cuckoo clock"),
    ("I'm a floating mountain of ice. What am I?", "An iceberg"),
    ("Stand still and I'll carry you up. What am I?", "An escalator"),
    ("Colors dance in my tube as you twist me. What am I?", "A kaleidoscope"),
    ("I carry a portable piece of day in the dark. What am I?", "A flashlight"),
    ("I build dams with teeth and logs. What am I?", "A beaver"),
    ("Painters hold me as they mix their paints. What am I?", "A palette"),
    ("I stand on one leg and wear pink. What am I?", "A flamingo"),
    ("Look through me to see what's light‑years away. What am I?", "A telescope"),
    ("I help with tasks as a music box. What am I?", "A music box"),
    ("I shade a stuffed face in the field. What am I?", "A scarecrow hat"),
    ("I'm made by animals that look like flowers. What am I?", "Coral"),
    ("I wear bristles for hair and paint for makeup. What am I?", "A paintbrush"),
    ("I waddle on ice and slide on my belly. What am I?", "A penguin"),
    ("Kids and grownups use me: a protractor. What am I?", "A protractor"),
    ("I'm water that sneaks onto leaves at night. What am I?", "Dew"),
    ("Throw me away and I might come back. What am I?", "A boomerang"),
    ("I'm a word made by mixing the letters of another. What am I?", "An anagram"),
    ("Kids and grownups use me: a surfboard. What am I?", "A surfboard"),
    ("I help with tasks as flippers. What am I?", "Flippers"),
    ("I live by the threshold and hate muddy boots. What am I?", "A doormat"),
    ("Kids and grownups use me: a doorstop. What am I?", "A doorstop"),
    ("I'm a glass cup that measures and mixes in labs. What am I?", "A beaker"),
    ("Touch me carefully—I'm prickly. What am I?", "A cactus"),
    ("I connect a falling person to drifting silk. What am I?", "A parachute cord"),
    ("My face never ticks, yet sunlight moves my hand. What am I?", "A sundial"),
    ("Kids and grownups use me: marshmallow sticks. What am I?", "Marshmallow sticks"),
    ("I carry deserts on my back in humps of fat. What am I?", "A camel"),
    ("I help you cross without getting wet. What am I?", "A bridge"),
    ("I spin with breezes to grind grain or make power. What am I?", "A windmill"),
    ("I make the smallest things look huge. What am I?", "A microscope"),
    ("Tiny worlds appear when you look through me. What am I?", "A microscope"),
    ("Walk me slowly to reach the heart. What am I?", "A labyrinth"),
    ("I creak when I need oil and hold the door in place. What am I?", "A hinge"),
]

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def check_for_duplicates_in_batch(riddles):
    normalized_riddles = {}
    duplicates = []

    for i, (question, answer) in enumerate(riddles):
        normalized_q = normalize_text(question)
        normalized_a = normalize_text(answer)

        key = (normalized_q, normalized_a)
        if key in normalized_riddles:
            duplicates.append((i, normalized_riddles[key], question, answer))
        else:
            normalized_riddles[key] = i

    return duplicates

def get_difficulty(question, answer):
    question_lower = question.lower()
    answer_lower = answer.lower()

    complex_words = ['complex', 'intricate', 'complicated', 'scientific', 'advanced']
    easy_words = ['simple', 'easy', 'basic', 'obvious']

    # Science/technical terms often indicate higher difficulty
    technical_terms = ['microscope', 'stethoscope', 'telescope', 'laboratory', 'scientific', 'x-ray', 'stalactite', 'stalagmite']

    if len(question) > 100 or any(word in question_lower for word in complex_words):
        return 'hard'
    elif any(term in question_lower or term in answer_lower for term in technical_terms):
        return 'hard'
    elif len(question) < 30 or any(word in question_lower for word in easy_words):
        return 'easy'
    else:
        return 'medium'

def generate_hint(question, answer):
    answer_clean = answer.replace('A ', '').replace('An ', '').replace('The ', '')
    if len(answer_clean) > 3:
        return f"It starts with '{answer_clean[0]}' and has {len(answer_clean)} letters"
    else:
        return f"Think about {answer_clean.lower()}"

conn = sqlite3.connect('riddles.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM riddles')
existing_count = cursor.fetchone()[0]
print(f"Found {existing_count} existing riddles in database")

print("Checking for duplicates within the new riddle batch...")
batch_duplicates = check_for_duplicates_in_batch(riddles_batch6)
if batch_duplicates:
    print(f"WARNING: Found {len(batch_duplicates)} exact duplicates in batch:")
    for dup_idx, orig_idx, question, answer in batch_duplicates[:10]:
        print(f"  Items {dup_idx} and {orig_idx} are identical: {question[:50].encode('ascii', 'ignore').decode('ascii')}...")
    if len(batch_duplicates) > 10:
        print(f"  ... and {len(batch_duplicates) - 10} more")

added_count = 0
skipped_count = 0

for question, answer in riddles_batch6:
    normalized_q = normalize_text(question)
    normalized_a = normalize_text(answer)

    cursor.execute('''
        SELECT id FROM riddles
        WHERE LOWER(REPLACE(REPLACE(REPLACE(question, '.', ''), '?', ''), '!', '')) = ?
        AND LOWER(REPLACE(REPLACE(REPLACE(answer, '.', ''), '?', ''), '!', '')) = ?
    ''', (normalized_q, normalized_a))

    if cursor.fetchone():
        skipped_count += 1
        continue

    difficulty = get_difficulty(question, answer)
    hint = generate_hint(question, answer)

    cursor.execute('''
        INSERT INTO riddles (question, answer, difficulty, hint)
        VALUES (?, ?, ?, ?)
    ''', (question, answer, difficulty, hint))

    added_count += 1
    print(f"ADDED [{difficulty}]: {question[:50].encode('ascii', 'ignore').decode('ascii')}...")

conn.commit()
conn.close()

print(f"\nBatch 6 Import Summary:")
print(f"- Riddles processed: {len(riddles_batch6)}")
print(f"- New riddles added: {added_count}")
print(f"- Duplicates skipped: {skipped_count}")
print(f"- Total riddles in database: {existing_count + added_count}")