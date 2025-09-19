import sqlite3
import re

riddles_batch5 = [
    ("Bird‑watchers love my double view. What am I?", "Binoculars"),
    ("I'm a vest that loves water. What am I?", "A life jacket"),
    ("Zip me up and snooze under the stars. What am I?", "A sleeping bag"),
    ("I turn pinwheels and push kites. What am I?", "Wind"),
    ("Touch me carefully—I'm prickly. What am I?", "A cactus"),
    ("I love long walks in the woods. What am I?", "A hiking boot"),
    ("I shave veggies, not faces. What am I?", "A peeler"),
    ("Flip a switch and I arrive. What am I?", "Light"),
    ("I follow your feet on bright days. What am I?", "A shadow"),
    ("I'm the little artist of camouflage. What am I?", "A chameleon"),
    ("I'm a stick that steers pixels. What am I?", "A joystick"),
    ("I hammer trees with my beak to find bugs. What am I?", "A woodpecker"),
    ("I give you two eyes that see far. What am I?", "Binoculars"),
    ("I'm a wire tornado in the kitchen. What am I?", "A whisk"),
    ("I'm a joint that helps doors swing. What am I?", "A hinge"),
    ("Whisper me or lose me. What am I?", "A secret"),
    ("I test the air and beep when it's smoky. What am I?", "A smoke alarm"),
    ("I bring faraway stars close to your eye. What am I?", "A telescope"),
    ("I turn far things near with paired lenses. What am I?", "Binoculars"),
    ("I'm the first to greet your feet at the door. What am I?", "A doormat"),
    ("Chains keep me close to a vest. What am I?", "A pocket watch"),
    ("Architects read me like a house map. What am I?", "A blueprint"),
    ("I'm a tube for shallow exploring. What am I?", "A snorkel"),
    ("I let the small through and keep the big. What am I?", "A sieve"),
    ("Tilt or tap and I guide the game. What am I?", "A joystick"),
    ("Singers hold me and I hum with sound. What am I?", "A microphone"),
    ("I speak only when you shout in a cave. What am I?", "An echo"),
    ("I'm made of water, but if you put me in water, I vanish. What am I?", "Ice"),
    ("I flatten dough into sheets without a press. What am I?", "A rolling pin"),
    ("I'm a plan on paper for buildings not yet built. What am I?", "A blueprint"),
    ("I'm light as a feather, yet no one can hold me for long. What am I?", "Breath"),
    ("Push a button and I carry you up or down. What am I?", "An elevator"),
    ("I wash floors with a hair‑do of strings. What am I?", "A mop"),
    ("I hover like a tiny helicopter and sip nectar. What am I?", "A hummingbird"),
    ("I'm a window in the roof that brings down the day. What am I?", "A skylight"),
    ("I keep time with a steady tick‑tock for practice. What am I?", "A metronome"),
    ("Swing my arm and the beat stays true. What am I?", "A metronome"),
    ("I like water more than dust. What am I?", "A mop"),
    ("I always know north without a brain. What am I?", "A compass"),
    ("People are happy to see me arch across the sky. What am I?", "A rainbow"),
    ("Chefs spin me to make things airy. What am I?", "A whisk"),
    ("Boaters wear me for safety. What am I?", "A life jacket"),
    ("I show walls before they exist. What am I?", "A blueprint"),
    ("Feed me and I live; give me a drink and I die. What am I?", "Fire"),
    ("Turn me over and time begins to trickle. What am I?", "An hourglass"),
    ("I'm a long, smooth board for the ocean. What am I?", "A surfboard"),
    ("Lines and spaces hold my code. What am I?", "A barcode"),
    ("I slide on snow without wheels. What am I?", "A sled"),
    ("One swipe and the skin is gone. What am I?", "A peeler"),
    ("Strike me and I sing one pure note. What am I?", "A tuning fork"),
    ("Kids ride me on sidewalks. What am I?", "A scooter"),
    ("Speak my name and I disappear. What am I?", "Silence"),
    ("I leave wet trails that soon dry. What am I?", "A mop"),
    ("I command the room's brightness with a click. What am I?", "A light switch"),
    ("Check me to catch the bus on time. What am I?", "A wristwatch"),
    ("I ride waves under your feet. What am I?", "A surfboard"),
    ("I fall without getting hurt and melt without crying. What am I?", "Snow"),
    ("You can hold me without touching me. What am I?", "Breath"),
    ("Look through me to visit the moon without leaving home. What am I?", "A telescope"),
    ("I run forever and never tire. What am I?", "Time"),
    ("My flat tail slaps the water as an alarm. What am I?", "A beaver"),
    ("I'm a board with wheels for tricks. What am I?", "A skateboard"),
    ("Stand still and I'll do the climbing. What am I?", "An escalator"),
    ("Paddling is how you catch me a ride. What am I?", "A surfboard"),
    ("I chase away the dark without lifting a thing. What am I?", "Light"),
    ("Musicians use my steady tone to tune. What am I?", "A tuning fork"),
    ("I point the way but never move. What am I?", "A compass"),
    ("I dance and crackle while I eat. What am I?", "Fire"),
    ("I keep rooms comfy by changing numbers. What am I?", "A thermostat"),
    ("I fills rooms until noise arrives. What am I?", "Silence"),
    ("Two bulbs and a narrow neck count moments grain by grain. What am I?", "An hourglass"),
    ("Witches ride me; cleaners guide me. What am I?", "A broom"),
    ("I'm a tray where colors meet and mingle. What am I?", "A palette"),
    ("I'm a little tray that likes dirt. What am I?", "A dustpan"),
    ("I make small things look huge. What am I?", "A microscope"),
    ("I change channels from across the room. What am I?", "A remote control"),
    ("I roar where the land suddenly ends. What am I?", "A waterfall"),
    ("I like to turn around mid‑flight. What am I?", "A boomerang"),
    ("Sand remembers me until waves erase me. What am I?", "Footsteps"),
    ("I mark a path without writing. What am I?", "Footsteps"),
    ("I'm a robot that never lands but keeps traveling. What am I?", "A satellite"),
    ("Your words bounce back as me. What am I?", "An echo"),
    ("Only the correct pattern can open me. What am I?", "A keyhole"),
    ("Two sticks, one meal—who am I?", "Chopsticks"),
    ("I run without legs and roar without a mouth. What am I?", "Wind"),
    ("I move in one direction and take you with me. What am I?", "Time"),
    ("Speak into me and I'll carry your words. What am I?", "A microphone"),
    ("I'm a mammal who loves the sea. What am I?", "A dolphin"),
    ("I lift people without stairs. What am I?", "An elevator"),
    ("You can count me, but not reverse me. What am I?", "Age"),
    ("I tell a scanner who I am without words. What am I?", "A barcode"),
    ("I'm a light with a handle for camping nights. What am I?", "A lantern"),
    ("Painters hold me as they mix paints. What am I?", "A palette"),
    ("Tiny teeth pluck metal combs to make my melody. What am I?", "A music box"),
    ("I can build islands with eruptions. What am I?", "A volcano"),
    ("I'm strong when kept and weak when broken. What am I?", "A promise"),
    ("I love ramps and rails. What am I?", "A skateboard"),
    ("I waddle on ice and slide on my belly. What am I?", "A penguin"),
    ("Black squares hide my message. What am I?", "A QR code"),
    ("I let your eyes see underwater. What am I?", "Swim goggles"),
    ("Click me on and shadows run away. What am I?", "A flashlight"),
    ("I have a deck, a bar, and two wheels. What am I?", "A scooter"),
    ("I'm the night in a windowless room. What am I?", "Darkness"),
    ("I let sunshine fall from above. What am I?", "A skylight"),
    ("I orbit high to help with maps and weather. What am I?", "A satellite"),
    ("I build dams with teeth and logs. What am I?", "A beaver"),
    ("Gamers grip me to fly and race on screens. What am I?", "A joystick"),
    ("I'm stripes that machines can read. What am I?", "A barcode"),
    ("I'm a spoon with a deep belly for serving. What am I?", "A ladle"),
    ("I wait for the sweep to deliver the mess. What am I?", "A dustpan"),
    ("I pour stew by the scoop. What am I?", "A ladle"),
    ("My doors open on different floors. What am I?", "An elevator"),
    ("I'm a picture made of seven colors, seen after rain. What am I?", "A rainbow"),
    ("I curve through the air back to where I started. What am I?", "A boomerang"),
    ("I stomp trails and keep feet dry. What am I?", "A hiking boot"),
    ("People give me their word to make me. What am I?", "A promise"),
    ("Press my button to hear my loud voice. What am I?", "A smoke alarm"),
    ("Plants cheer when I visit. What am I?", "Rain"),
    ("Submarines use me to look above the waves. What am I?", "A periscope"),
    ("I go up but never come back down. What am I?", "Age"),
    ("Hold me steady as crumbs come in. What am I?", "A dustpan"),
    ("Before bulbs, I used to burn; now I shine with batteries. What am I?", "A lantern"),
    ("I don't stab or scoop; I pinch your dinner. What am I?", "Chopsticks"),
    ("I'm a round handle for rooms. What am I?", "A doorknob"),
    ("Pull me uphill; ride me down. What am I?", "A sled"),
    ("I'm the hand that knocks when guests visit. What am I?", "A doorknocker"),
    ("I make your feet into fins. What am I?", "Flippers"),
    ("I'm a square maze that a phone understands. What am I?", "A QR code"),
    ("Shake me and flour falls like dust. What am I?", "A sieve"),
    ("Travelers trust my tiny needle. What am I?", "A compass"),
    ("Point and press; I obey your thumb. What am I?", "A remote control"),
    ("I'm a bed that rolls up. What am I?", "A sleeping bag"),
    ("I'm solid until I warm up. What am I?", "Ice"),
    ("Clouds pass over my glass ceiling. What am I?", "A skylight"),
    ("I can fill a room but take up no space. What am I?", "Light"),
    ("I'm a tube that stretches your sight into space. What am I?", "A telescope"),
    ("I'm a pair that works as one to pick up food. What am I?", "Chopsticks"),
    ("I'm a warm burrito for campers. What am I?", "A sleeping bag"),
    ("Before doorbells, people lifted me to make a sound. What am I?", "A doorknocker"),
    ("Thrown away, I sometimes return. What am I?", "A boomerang"),
    ("I fly underwater instead of in the sky. What am I?", "A penguin"),
    ("I'm only safe when kept quiet. What am I?", "A secret"),
    ("I let you peek over walls or from underwater. What am I?", "A periscope"),
    ("Wear me to keep your music private. What am I?", "Headphones"),
    ("Divers wear me for speed. What am I?", "Flippers"),
    ("I change my colors to blend in. What am I?", "A chameleon"),
    ("I undress potatoes and carrots. What am I?", "A peeler"),
    ("The more of me you have, the less you see. What am I?", "Darkness"),
    ("I love winter hills. What am I?", "A sled"),
    ("I store water in the desert. What am I?", "A cactus"),
    ("Skates love my cold surface. What am I?", "Ice"),
    ("Up I shine; down I rest. What am I?", "A light switch"),
    ("I live by the threshold and dislike muddy boots. What am I?", "A doormat"),
    ("I'm a jewel that hums in midair. What am I?", "A hummingbird"),
    ("Symmetry spins inside me. What am I?", "A kaleidoscope"),
    ("I wear spines for armor and drink rarely. What am I?", "A cactus"),
    ("I'm winter's confetti. What am I?", "Snow"),
    ("I tick in a pocket instead of on a wall. What am I?", "A pocket watch"),
    ("Straps hold me on while you swim. What am I?", "Swim goggles"),
    ("I put concerts right next to your ears. What am I?", "Headphones"),
    ("I'm a smart swimmer who talks in clicks and whistles. What am I?", "A dolphin"),
    ("I make light and heat but fear rain. What am I?", "Fire"),
    ("Cookies and pies meet me before the oven. What am I?", "A rolling pin"),
    ("Push and roll to cruise with me. What am I?", "A skateboard"),
    ("I hide time in a little locket. What am I?", "A pocket watch"),
    ("I beat without hands to fluff eggs and cream. What am I?", "A whisk"),
    ("I trap snow in a sphere. What am I?", "A snow globe"),
    ("You can break me even if you never pick me up. What am I?", "A promise"),
    ("Umbrellas pop up when I arrive. What am I?", "Rain"),
    ("Kick with me to move faster underwater. What am I?", "Flippers"),
    ("Tiny worlds appear when you look through me. What am I?", "A microscope"),
    ("I'm a river that tumbles off a cliff. What am I?", "A waterfall"),
    ("Open my lid and hear my song. What am I?", "A music box"),
    ("My wings beat faster than you can count. What am I?", "A hummingbird"),
    ("I measure time with falling grains and flip to start again. What am I?", "An hourglass"),
    ("North seeks south when I'm near. What am I?", "A magnet"),
    ("I'm a bird who wears a tuxedo and swims. What am I?", "A penguin"),
    ("Careful with your fingers when you use me! What am I?", "A grater"),
    ("Lava sleeps in my heart until I wake. What am I?", "A volcano"),
    ("I help you float when you fall in. What am I?", "A life jacket"),
    ("Colors dance in my tube as you twist me. What am I?", "A kaleidoscope"),
    ("If you share me, you no longer have me. What am I?", "A secret"),
    ("I make quiet voices loud on stage. What am I?", "A microphone"),
    ("I set the heat without cooking. What am I?", "A thermostat"),
    ("I look like a letter but sound like a pitch. What am I?", "A tuning fork"),
    ("Laces tight, I'm ready for rocks and mud. What am I?", "A hiking boot"),
    ("I attract some metals but ignore wood and glass. What am I?", "A magnet"),
    ("The more you take, the more you leave behind. What am I?", "Footsteps"),
    ("I turn to open opportunities. What am I?", "A doorknob"),
    ("I tell time without hands or numbers, guided by a shadow. What am I?", "A sundial"),
    ("Artists wave me like a wand of paint. What am I?", "A paintbrush"),
    ("I announce visitors with a clang. What am I?", "A doorknocker"),
    ("Kick and glide; I'll carry you along. What am I?", "A scooter"),
    ("I'm a pocket‑sized beam of light. What am I?", "A flashlight"),
    ("I'm a voice that doesn't belong to a mouth. What am I?", "An echo"),
    ("I have cushions for ears and a wire or none at all. What am I?", "Headphones"),
    ("Pianists love my constant tempo. What am I?", "A metronome"),
    ("Pair me with fins and a mask. What am I?", "A snorkel"),
    ("Dipped in color, I leave strokes on canvas. What am I?", "A paintbrush"),
    ("I'm a cylinder that smooths your dough. What am I?", "A rolling pin"),
    ("I keep colors handy like a plate. What am I?", "A palette"),
    ("Hang me up and I glow all around. What am I?", "A lantern"),
    ("I mark hours when the sun is out. What am I?", "A sundial"),
    ("I'm a house you can fold and carry. What am I?", "A tent"),
    ("Wipe your shoes on me before you enter. What am I?", "A doormat"),
    ("Point a camera at me and a link appears. What am I?", "A QR code"),
    ("Poles and cloth make me cozy outdoors. What am I?", "A tent"),
    ("I wrap around your arm to tell time. What am I?", "A wristwatch"),
    ("Oil me when I creak; I hold the door in place. What am I?", "A hinge"),
    ("I circle Earth and carry calls and pictures. What am I?", "A satellite"),
    ("Shake me and winter starts again. What am I?", "A snow globe"),
    ("Without me, doors wouldn't move. What am I?", "A hinge"),
    ("I wear a hard hat of feathers. What am I?", "A woodpecker"),
    ("I carry a little piece of day into the dark. What am I?", "A flashlight"),
    ("I let you breathe while your face is in the water. What am I?", "A snorkel"),
    ("My steps never stop. What am I?", "An escalator"),
    ("I fog a mirror but can't be seen for long. What am I?", "Breath"),
    ("I have hands but never clap. What am I?", "A wristwatch"),
    ("A flick of me turns day into night and back again—indoors. What am I?", "A light switch"),
    ("I'm a metal mountain full of sharp holes. What am I?", "A grater"),
    ("I boss the TV around with buttons. What am I?", "A remote control"),
    ("I drum on trunks to send messages. What am I?", "A woodpecker"),
    ("I grow in sunlight and hide in the dark. What am I?", "A shadow"),
    ("I wear bristles for hair. What am I?", "A paintbrush"),
    ("I turn cheese into tiny snow. What am I?", "A grater"),
    ("I come down in drops and fill rivers. What am I?", "Rain"),
    ("I bend light with mirrors so you can see from below. What am I?", "A periscope"),
    ("I dive into soup and come up with a bowl. What am I?", "A ladle"),
    ("I turn and make endless patterns from bits of glass. What am I?", "A kaleidoscope"),
    ("I grows each birthday and never shrinks. What am I?", "Age"),
    ("Dust runs away when I get to work. What am I?", "A broom"),
    ("I scream to wake you when danger is in the air. What am I?", "A smoke alarm"),
    ("You can see me but never touch me; I copy your shape. What am I?", "A shadow"),
    ("I'm a net for tiny things in the kitchen. What am I?", "A sieve"),
    ("I can be broken without being touched. What am I?", "Silence"),
    ("Peer through me or use the right match to pass. What am I?", "A keyhole"),
    ("I play a tune when you wind me up. What am I?", "A music box"),
    ("I sweep but never sleep. What am I?", "A broom"),
    ("My face never ticks; sunlight moves my hand. What am I?", "A sundial"),
    ("Sunlight and rain team up to make me. What am I?", "A rainbow"),
    ("I'm nature's busy engineer. What am I?", "A beaver"),
    ("My eyes can look two ways at once. What am I?", "A chameleon"),
    ("Germs and cells become giants in my glass. What am I?", "A microscope"),
    ("I pop up in camps and zip shut at night. What am I?", "A tent"),
    ("I hide everything until light appears. What am I?", "Darkness"),
    ("Mist and rainbows like to visit me. What am I?", "A waterfall"),
    ("I pull without touching, but only certain things. What am I?", "A magnet"),
    ("Too hot, too cold—adjust me to just right. What am I?", "A thermostat"),
    ("I'm a mountain that sometimes breathes fire. What am I?", "A volcano"),
    ("I'm small and picky about which teeth I let in. What am I?", "A keyhole"),
    ("Grab and twist; I'll let you in. What am I?", "A doorknob"),
    ("You can spend me but not save me forever. What am I?", "Time"),
    ("I'm a staircase that moves on my own. What am I?", "An escalator"),
    ("I keep the pool out of your sight. What am I?", "Swim goggles"),
    ("I surf waves and leap for fun. What am I?", "A dolphin"),
    ("You can't see me, but I move the trees. What am I?", "Wind"),
    ("A tiny town lives in my glass. What am I?", "A snow globe"),
    ("I blanket the world in white. What am I?", "Snow"),
    ("I'm a vest that loves water. Who am I?", "A life jacket"),
    ("I turn pinwheels and push kites. Guess me.", "Wind"),
    ("Touch me carefully—I am prickly. What am I?", "A cactus"),
    ("I love long walks in the woods. Who am I?", "A hiking boot"),
    ("I shave veggies, not faces. Can you name me?", "A peeler"),
    ("Flip a switch and I arrive. Who am I?", "Light"),
    ("I follow your feet on bright days. Can you name me?", "A shadow"),
    ("I am the little artist of camouflage. What am I?", "A chameleon"),
    ("I am a stick that steers pixels. What am I?", "A joystick"),
    ("I hammer trees with my beak to find bugs. Can you name me?", "A woodpecker"),
    ("I give you two eyes that see far. Can you name me?", "Binoculars"),
    ("I'm a wire tornado in the kitchen. Who am I?", "A whisk"),
    ("I'm a joint that helps doors swing. Can you name me?", "A hinge"),
    ("Whisper me or lose me. Who am I?", "A secret"),
    ("I bring faraway stars close to your eye. Who am I?", "A telescope"),
    ("I turn far things near with paired lenses. Can you name me?", "Binoculars"),
    ("Chains keep me close to a vest. Who am I?", "A pocket watch"),
    ("Architects read me like a house map. Who am I?", "A blueprint"),
    ("I let the small through and keep the big. Guess me.", "A sieve"),
    ("Singers hold me and I hum with sound. Who am I?", "A microphone"),
    ("I speak only when you shout in a cave. Who am I?", "An echo"),
    ("I am made of water, but if you put me in water, I vanish. Can you name me?", "Ice"),
    ("I flatten dough into sheets without a press. Who am I?", "A rolling pin"),
    ("I'm light as a feather, yet no one can hold me for long. Can you name me?", "Breath"),
    ("I wash floors with a hair‑do of strings. Can you name me?", "A mop"),
    ("I'm a window in the roof that brings down the day. Guess me.", "A skylight"),
    ("I keep time with a steady tick‑tock for practice. Can you name me?", "A metronome"),
    ("Swing my arm and the beat stays true. Who am I?", "A metronome"),
    ("I like water more than dust. Can you name me?", "A mop"),
    ("People are happy to see me arch across the sky. Guess me.", "A rainbow"),
    ("Chefs spin me to make things airy. Can you name me?", "A whisk"),
    ("Boaters wear me for safety. Can you name me?", "A life jacket"),
    ("I'm a long, smooth board for the ocean. Guess me.", "A surfboard"),
    ("Lines and spaces hold my code. Can you name me?", "A barcode"),
    ("I slide on snow without wheels. Can you name me?", "A sled"),
    ("One swipe and the skin is gone. Who am I?", "A peeler"),
    ("Strike me and I sing one pure note. Guess me.", "A tuning fork"),
    ("Kids ride me on sidewalks. Guess me.", "A scooter"),
    ("I command the room's brightness with a click. Can you name me?", "A light switch"),
    ("Check me to catch the bus on time. Who am I?", "A wristwatch"),
    ("I ride waves under your feet. Can you name me?", "A surfboard"),
    ("I fall without getting hurt and melt without crying. Can you name me?", "Snow"),
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

    if len(question) > 100 or any(word in question_lower for word in ['complex', 'intricate', 'complicated']):
        return 'hard'
    elif len(question) < 30 or any(word in question_lower for word in ['simple', 'easy', 'basic']):
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
batch_duplicates = check_for_duplicates_in_batch(riddles_batch5)
if batch_duplicates:
    print(f"WARNING: Found {len(batch_duplicates)} exact duplicates in batch:")
    for dup_idx, orig_idx, question, answer in batch_duplicates[:10]:
        print(f"  Items {dup_idx} and {orig_idx} are identical: {question[:50]}...")
    if len(batch_duplicates) > 10:
        print(f"  ... and {len(batch_duplicates) - 10} more")

added_count = 0
skipped_count = 0

for question, answer in riddles_batch5:
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

print(f"\nBatch 5 Import Summary:")
print(f"- Riddles processed: {len(riddles_batch5)}")
print(f"- New riddles added: {added_count}")
print(f"- Duplicates skipped: {skipped_count}")
print(f"- Total riddles in database: {existing_count + added_count}")