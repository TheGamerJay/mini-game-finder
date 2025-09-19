#!/usr/bin/env python3
import sqlite3
import re
import string

# New riddles batch 2
riddles_batch2 = [
    ("What has keys but can't open a thing?", "A piano"),
    ("What has pages but doesn't turn one alone?", "A book"),
    ("What has hands and a face but never needs gloves?", "A clock"),
    ("What has a neck and a cap but no head?", "A bottle"),
    ("What runs but never walks and has a bed but never sleeps?", "A river"),
    ("What is full of holes yet still holds water?", "A sponge"),
    ("What invention lets you look through a wall?", "A window"),
    ("What can be cracked, made, told, and played?", "A joke"),
    ("What goes up when the rain comes down?", "An umbrella"),
    ("What gets sharper the more you use it?", "Your brain"),
    ("What has bark but never bites?", "A tree"),
    ("What has roots that no one sees and is taller than trees?", "A mountain"),
    ("What gets wetter the more it dries?", "A towel"),
    ("What has a head and a tail but no body?", "A coin"),
    ("I'm tall when I'm young and short when I'm old. What am I?", "A candle"),
    ("I fly without wings and cry without eyes. What am I?", "A cloud"),
    ("I speak without a mouth and echo your shout. What am I?", "An echo"),
    ("What belongs to you but is used by others more than you?", "Your name"),
    ("What has many needles but cannot sew?", "A Christmas tree"),
    ("What has four wheels and flies?", "A garbage truck"),
    ("What has many teeth but never bites?", "a comb"),
    ("I show lots of teeth but never smile. What am I?", "a comb"),
    ("Which tool has teeth that tame hair, not food?", "a comb"),
    ("What has rows of little teeth that never chew?", "a zipper"),
    ("I use my teeth to keep things together. What am I?", "a zipper"),
    ("What closes with teeth but never eats?", "a zipper"),
    ("What has bark, leaves, and rings but no voice or fingers?", "a tree"),
    ("What wears green in summer and none in winter?", "a tree"),
    ("What stands in one place but leaves every year?", "a tree"),
    ("What has a spine but no bones?", "a book"),
    ("What's full of words yet stays quiet on the shelf?", "a book"),
    ("What speaks to your eyes but has no mouth?", "a book"),
    ("What flows to the sea but never walks a step?", "a river"),
    ("What carves canyons without tools?", "a river"),
    ("What has a mouth that never talks and a bed that never sleeps?", "a river"),
    ("What follows you by day and hides by night?", "a shadow"),
    ("What stretches tall in evening and shrinks at noon?", "a shadow"),
    ("You can see me but never touch me. What am I?", "a shadow"),
    ("What brings shade without branches?", "a cloud"),
    ("What paints the sky then drifts away?", "a cloud"),
    ("What cries without eyes?", "a cloud"),
    ("What dies if it drinks and lives while it eats air?", "a candle"),
    ("What is quick when thin and slow when fat?", "a candle"),
    ("What gives light but fears a gust?", "a candle"),
    ("Where do letters live before words are born?", "a keyboard"),
    ("What has keys that type but open no doors?", "a keyboard"),
    ("What lets you turn thoughts into text?", "a keyboard"),
    ("What shows truth reversed?", "a mirror"),
    ("Smile at me and I smile back. What am I?", "a mirror"),
    ("What reflects but never remembers?", "a mirror"),
    ("What wears a snow cap and never feels cold?", "a mountain"),
    ("What reaches clouds without growing leaves?", "a mountain"),
    ("What stands tallest but never takes a step?", "a mountain"),
    ("What goes around a yard but never goes inside?", "a fence"),
    ("What divides neighbors but keeps no secrets?", "a fence"),
    ("What has many posts but never mails a letter?", "a fence"),
    ("What leaves a trail wherever it goes and grows shorter with use?", "a pencil"),
    ("What can write a future and erase a past?", "a pencil"),
    ("What draws lines without walking a line?", "a pencil"),
    ("What guides ships by standing still?", "a lighthouse"),
    ("What shines for others and sleeps by day?", "a lighthouse"),
    ("What warns of rocks without saying a word?", "a lighthouse"),
    ("What glitters though made of fire?", "a star"),
    ("What writes constellations across the night?", "a star"),
    ("What twinkles far away but burns up close?", "a star"),
    ("What is born in clouds and dies on your tongue?", "a snowflake"),
    ("What is unique, silent, and cold?", "a snowflake"),
    ("What falls without making a sound?", "a snowflake"),
    ("What tugs at a string from the sky?", "a kite"),
    ("What dances only when the wind plays music?", "a kite"),
    ("What flies best when it's held down?", "a kite"),
    ("What travels the world and rarely sees the sun?", "a submarine"),
    ("What hears the ocean's heartbeat with no ears?", "a submarine"),
    ("What dives deep but isn't a fish?", "a submarine"),
    ("What fights plaque without a sword?", "a toothbrush"),
    ("What has bristles but not a beard?", "a toothbrush"),
    ("What works every morning and night without pay?", "a toothbrush"),
    ("What is small enough to hide in a pocket but big enough to become a forest?", "a seed"),
    ("What dreams of trees inside a shell?", "a seed"),
    ("What sleeps in soil and wakes as a plant?", "a seed"),
    ("What keeps cool even in summer and repeats what you say?", "a cave"),
    ("What's a home for bats and echoes?", "a cave"),
    ("What is hollow yet full of stone?", "a cave"),
    ("What sings when wind runs through it?", "a whistle"),
    ("What calls players to start and stop?", "a whistle"),
    ("What makes a sound without a tongue?", "a whistle"),
    ("What measures without judging?", "a ruler"),
    ("What draws straight lines without ink?", "a ruler"),
    ("What keeps inches in line?", "a ruler"),
    ("What freezes time with a click?", "a camera"),
    ("What has a lens to see but no brain to think?", "a camera"),
    ("What shoots without bullets and captures memories?", "a camera"),
    ("What connects places without moving an inch?", "a road"),
    ("What has lanes but no waves?", "a road"),
    ("What runs through towns and fields but never moves?", "a road"),
    ("What holds many letters but cannot read?", "a mailbox"),
    ("What raises a flag that isn't a country?", "a mailbox"),
    ("What waits by the curb for news?", "a mailbox"),
    ("What runs all day to keep cool?", "a refrigerator"),
    ("What fears the door left open?", "a refrigerator"),
    ("What chills food but warms the room?", "a refrigerator"),
    ("What spins in circles yet has no legs?", "a coin"),
    ("What has a head and a tail and pays attention?", "a coin"),
    ("What flips to help you decide?", "a coin"),
    ("I'm present in every letter of South, absent from East, North, Center, West. What am I?", "The letter 'U'"),
    ("I appear in Europe yet in West I'm gone. Who am I?", "The letter 'O'"),
    ("I appear in Square yet in Pentagon, Hexagon, Rhombus, Circle I'm gone. Who am I?", "The letter 'Q'"),
    ("In Friday I'm there; in Sunday, Tuesday, Monday, Wednesday, Saturday, Thursday I disappear. Who am I?", "The letter 'F'"),
    ("I appear in Wednesday, Thursday, Monday, Tuesday yet in Jupiter, Saturn, Venus I'm gone. Who am I?", "The letter 'D'"),
    ("In Triangle, Rectangle, Pentagon I'm there; in Saxophone, Trumpet, Cello, Piano I disappear. Who am I?", "The letter 'G'"),
    ("I'm present in every letter of Lion, Donkey, absent from Fox. What am I?", "The letter 'N'"),
    ("In Gray, Orange, Black I'm there; in Red, Indigo, White I disappear. Who am I?", "The letter 'A'"),
    ("I appear in Apple, Plum, Grape yet in White, Indigo, Blue I'm gone. Who am I?", "The letter 'P'"),
    ("I appear in Oval yet in Octagon, Rhombus I'm gone. Who am I?", "The letter 'V'"),
    ("I appear in February yet in January, May, April I'm gone. Who am I?", "The letter 'B'"),
    ("In Hockey, Football, Golf I'm there; in Baseball, Tennis, Rugby I disappear. Who am I?", "The letter 'O'"),
    ("Spot me in Mercury, Jupiter; you won't find me in Kiwi. What am I?", "The letter 'U'"),
    ("Spot me in Lime; you won't find me in Bear. What am I?", "The letter 'M'"),
    ("I'm present in every letter of Hexagon, Octagon, absent from Triangle, Square, Rectangle, Circle. What am I?", "The letter 'O'"),
    ("I'm present in every letter of Iron, Oxygen, absent from Grape. What am I?", "The letter 'O'"),
    ("You'll find me in all of Helium, Lead, Sulfur but in none of Africa, Oceania, Europe. What am I?", "The letter 'L'"),
    ("Spot me in Mercury, Saturn, Neptune, Jupiter; you won't find me in Mars, Earth. What am I?", "The letter 'U'"),
    ("You'll find me in all of December, March but in none of Red, Brown. What am I?", "The letter 'M'"),
    ("In Antarctica I'm there; in Asia, Africa, Europe, Oceania I disappear. Who am I?", "The letter 'T'"),
    ("In Wednesday, Sunday I'm there; in Tuesday I disappear. Who am I?", "The letter 'N'"),
    ("I'm present in every letter of Hockey, absent from Lemon. What am I?", "The letter 'Y'"),
    ("In Rabbit I'm there; in Neptune, Earth, Mars I disappear. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Kiwi, absent from Plum, Pear, Papaya, Mango. What am I?", "The letter 'I'"),
    ("I'm present in every letter of Gold, Nitrogen, absent from Lead, Carbon. What am I?", "The letter 'G'"),
    ("You'll find me in all of Moose but in none of Whale, Bear. What am I?", "The letter 'O'"),
    ("I appear in America, Oceania yet in Brown, Orange, Red, Pink I'm gone. Who am I?", "The letter 'C'"),
    ("Spot me in Giraffe; you won't find me in Eagle, Otter, Monkey, Moose, Rabbit, Cobra. What am I?", "The letter 'F'"),
    ("I appear in Jupiter, Saturn yet in Africa, Asia, America I'm gone. Who am I?", "The letter 'U'"),
    ("You'll find me in all of Sunday, Monday, Tuesday but in none of Yak, Fox, Otter. What am I?", "The letter 'D'"),
    ("I appear in Sunday, Wednesday yet in Tuesday, Saturday, Friday I'm gone. Who am I?", "The letter 'N'"),
    ("In Shark I'm there; in Oxygen, Lead, Silver, Sulfur I disappear. Who am I?", "The letter 'H'"),
    ("I'm present in every letter of Wednesday, Tuesday, Saturday, absent from Brown, White, Black. What am I?", "The letter 'S'"),
    ("Spot me in Jupiter, Saturn, Earth; you won't find me in Mercury, Venus. What am I?", "The letter 'T'"),
    ("I'm present in every letter of Sunday, Wednesday, Monday, Saturday, absent from Star. What am I?", "The letter 'Y'"),
    ("You'll find me in all of Wolf, Fox but in none of Venus. What am I?", "The letter 'O'"),
    ("I'm present in every letter of Rugby, absent from Tennis, Hockey, Soccer, Cricket, Basketball. What am I?", "The letter 'U'"),
    ("You'll find me in all of Mango, Pear but in none of Lime, Cherry, Kiwi. What am I?", "The letter 'A'"),
    ("Spot me in Guitar, Piano, Harp; you won't find me in Oxygen, Sulfur, Silver, Tin. What am I?", "The letter 'A'"),
    ("In Monkey I'm there; in Indigo, White I disappear. Who am I?", "The letter 'M'"),
    ("I appear in Violin yet in Peach, Apple I'm gone. Who am I?", "The letter 'V'"),
    ("I'm present in every letter of West, absent from East, North, Center. What am I?", "The letter 'W'"),
    ("I'm present in every letter of Kiwi, absent from Earth, Saturn, Mars. What am I?", "The letter 'W'"),
    ("I'm present in every letter of South, absent from Mars, Earth, Saturn. What am I?", "The letter 'O'"),
    ("You'll find me in all of Africa, America, Oceania, Asia but in none of Lemon, Banana, Orange. What am I?", "The letter 'I'"),
    ("You'll find me in all of Antarctica, Europe, Africa but in none of Hockey, Golf, Volleyball, Football. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Sulfur, absent from Cello. What am I?", "The letter 'S'"),
    ("I appear in Yellow yet in Tennis, Rugby I'm gone. Who am I?", "The letter 'O'"),
    ("I'm present in every letter of October, absent from Carbon. What am I?", "The letter 'E'"),
    ("Spot me in Oxygen; you won't find me in Lead, Silver, Nitrogen. What am I?", "The letter 'Y'"),
    ("I'm present in every letter of Baseball, Volleyball, absent from Rugby. What am I?", "The letter 'E'"),
    ("I appear in Pink yet in Orange I'm gone. Who am I?", "The letter 'I'"),
    ("In Moose I'm there; in Monkey, Cobra I disappear. Who am I?", "The letter 'S'"),
    ("I'm present in every letter of June, October, February, December, absent from April, July. What am I?", "The letter 'E'"),
    ("Spot me in Tuesday, Sunday, Monday; you won't find me in Neptune. What am I?", "The letter 'A'"),
    ("I appear in Friday yet in Sunday, Thursday I'm gone. Who am I?", "The letter 'I'"),
    ("In Friday, Thursday, Saturday, Monday I'm there; in Rhombus I disappear. Who am I?", "The letter 'Y'"),
    ("I appear in Piano yet in Pink I'm gone. Who am I?", "The letter 'O'"),
    ("You'll find me in all of North, Center but in none of West, East. What am I?", "The letter 'N'"),
    ("In May, December I'm there; in Soccer, Football I disappear. Who am I?", "The letter 'M'"),
    ("In Wednesday, Friday I'm there; in West, North, East, Center I disappear. Who am I?", "The letter 'Y'"),
    ("You'll find me in all of Otter but in none of Lime, Apple, Papaya. What am I?", "The letter 'O'"),
    ("Spot me in Lemon; you won't find me in Cherry, Banana, Kiwi. What am I?", "The letter 'O'"),
    ("You'll find me in all of America, Asia, Antarctica, Africa but in none of Lead, Copper, Sulfur, Carbon. What am I?", "The letter 'I'"),
    ("I appear in Mercury yet in Uranus, Earth, Saturn I'm gone. Who am I?", "The letter 'C'"),
    ("Spot me in Indigo, Red; you won't find me in Rugby. What am I?", "The letter 'D'"),
    ("In July I'm there; in Brown, Violet, Black, Indigo I disappear. Who am I?", "The letter 'J'"),
    ("In West I'm there; in North, Center, East, South I disappear. Who am I?", "The letter 'W'"),
    ("You'll find me in all of Football, Volleyball but in none of Iron, Gold. What am I?", "The letter 'A'"),
    ("Spot me in Oxygen; you won't find me in February, March, July. What am I?", "The letter 'X'"),
    ("I'm present in every letter of Tennis, absent from Golf, Soccer, Football, Baseball. What am I?", "The letter 'I'"),
    ("I'm present in every letter of February, August, January, absent from Volleyball. What am I?", "The letter 'U'"),
    ("In South, East, West, North I'm there; in Black I disappear. Who am I?", "The letter 'T'"),
    ("In Golf, Baseball, Basketball I'm there; in Hockey, Tennis, Cricket I disappear. Who am I?", "The letter 'L'"),
    ("I appear in West yet in Golf, Baseball, Cricket I'm gone. Who am I?", "The letter 'W'"),
    ("I appear in Oceania yet in Europe, Africa I'm gone. Who am I?", "The letter 'N'"),
    ("I'm present in every letter of Lime, Grape, Apple, absent from Kiwi. What am I?", "The letter 'E'"),
    ("Spot me in Cobra; you won't find me in Eagle, Yak, Donkey, Wolf. What am I?", "The letter 'B'"),
    ("You'll find me in all of Tennis, Cricket, Basketball but in none of Sunday, Friday, Monday. What am I?", "The letter 'T'"),
    ("Spot me in Circle; you won't find me in Triangle, Star, Square. What am I?", "The letter 'C'"),
    ("Spot me in Antarctica, Oceania; you won't find me in Center, West, East, South. What am I?", "The letter 'I'"),
    ("I'm present in every letter of Rugby, Football, absent from Tennis. What am I?", "The letter 'B'"),
    ("I appear in Uranus, Neptune yet in Mars I'm gone. Who am I?", "The letter 'U'"),
    ("You'll find me in all of February, August but in none of Oceania, Antarctica, Asia, Africa. What am I?", "The letter 'U'"),
    ("In Violet I'm there; in Pink, Gray I disappear. Who am I?", "The letter 'E'"),
    ("I appear in North yet in Africa, Antarctica, Asia I'm gone. Who am I?", "The letter 'H'"),
    ("I'm present in every letter of Monday, absent from Thursday, Sunday. What am I?", "The letter 'M'"),
    ("In March I'm there; in October, April, July, June I disappear. Who am I?", "The letter 'H'"),
    ("I appear in Triangle, Hexagon, Square, Circle yet in Black I'm gone. Who am I?", "The letter 'E'"),
    ("You'll find me in all of Violin but in none of Rhombus, Circle, Octagon, Hexagon. What am I?", "The letter 'V'"),
    ("In America, Asia I'm there; in North, South I disappear. Who am I?", "The letter 'A'"),
    ("I appear in Silver, Hydrogen yet in Guitar I'm gone. Who am I?", "The letter 'E'"),
    ("You'll find me in all of East but in none of West, Center, South, North. What am I?", "The letter 'A'"),
    ("Spot me in America; you won't find me in Europe, Antarctica. What am I?", "The letter 'M'"),
    ("Spot me in Tin, Iron; you won't find me in Baseball, Rugby, Basketball. What am I?", "The letter 'N'"),
    ("In South I'm there; in North, West, Center I disappear. Who am I?", "The letter 'U'"),
    ("In Wolf I'm there; in Otter, Fox I disappear. Who am I?", "The letter 'W'"),
    ("I appear in Sunday, Friday, Tuesday, Monday yet in Square I'm gone. Who am I?", "The letter 'D'"),
    ("You'll find me in all of Monkey, Donkey but in none of Hydrogen, Iron, Gold, Nitrogen. What am I?", "The letter 'K'"),
    ("You'll find me in all of Basketball, Rugby but in none of Tennis. What am I?", "The letter 'B'"),
    ("You'll find me in all of Square but in none of Cricket, Golf. What am I?", "The letter 'A'"),
    ("Spot me in Pink; you won't find me in Football, Golf, Tennis. What am I?", "The letter 'P'"),
    ("I'm present in every letter of Oceania, absent from Africa, Europe, Asia. What am I?", "The letter 'N'"),
    ("I appear in North, West, East, South yet in Mango I'm gone. Who am I?", "The letter 'T'"),
    ("I appear in Drum, Clarinet yet in Neptune I'm gone. Who am I?", "The letter 'R'"),
    ("I appear in Lime yet in Africa, Europe, America I'm gone. Who am I?", "The letter 'L'"),
    ("I'm present in every letter of Giraffe, absent from Circle, Octagon, Pentagon, Oval. What am I?", "The letter 'F'"),
    ("Spot me in Earth, Jupiter; you won't find me in Tennis. What am I?", "The letter 'R'"),
    ("In Uranus, Mercury, Jupiter I'm there; in Pear, Grape, Orange, Papaya I disappear. Who am I?", "The letter 'U'"),
    ("Spot me in May; you won't find me in Saxophone, Clarinet, Flute. What am I?", "The letter 'Y'"),
    ("I appear in Basketball, Soccer, Baseball yet in Volleyball I'm gone. Who am I?", "The letter 'S'"),
    ("You'll find me in all of Square but in none of August, October. What am I?", "The letter 'Q'"),
    ("I appear in Africa yet in Oceania, America, Antarctica I'm gone. Who am I?", "The letter 'F'"),
    ("I appear in Sunday yet in Basketball, Football, Rugby, Volleyball I'm gone. Who am I?", "The letter 'D'"),
    ("Spot me in Monkey; you won't find me in Iron, Lead, Hydrogen, Oxygen. What am I?", "The letter 'K'"),
    ("In Hexagon, Triangle, Rectangle, Star I'm there; in South, Center I disappear. Who am I?", "The letter 'A'"),
    ("In Soccer I'm there; in Indigo, Black I disappear. Who am I?", "The letter 'R'"),
    ("In Saturday, Sunday, Thursday, Wednesday I'm there; in Oceania, Africa, Europe, America I disappear. Who am I?", "The letter 'S'"),
    ("Spot me in Helium, Lead, Silver; you won't find me in March. What am I?", "The letter 'E'"),
    ("Spot me in Mercury, Uranus; you won't find me in Earth, Mars. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Tuesday, Sunday, absent from Antarctica, Asia, America, Oceania. What am I?", "The letter 'D'"),
    ("In Oxygen, Iron, Copper, Nitrogen I'm there; in America I disappear. Who am I?", "The letter 'O'"),
    ("I appear in Saturday yet in Friday, Sunday I'm gone. Who am I?", "The letter 'T'"),
    ("I'm present in every letter of Lime, absent from Tuesday, Saturday, Thursday, Friday. What am I?", "The letter 'L'"),
    ("Spot me in Venus, Neptune; you won't find me in Square. What am I?", "The letter 'N'"),
    ("You'll find me in all of Saturn but in none of August, October. What am I?", "The letter 'N'"),
    ("You'll find me in all of Antarctica, Africa, America, Oceania but in none of Asia. What am I?", "The letter 'C'"),
    ("Spot me in Monday, Friday, Thursday, Saturday; you won't find me in Orange, Red. What am I?", "The letter 'Y'"),
    ("I appear in America, Oceania yet in North, East I'm gone. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Piano, absent from Saturn, Uranus, Mars. What am I?", "The letter 'I'"),
    ("In Basketball, Football, Baseball, Rugby I'm there; in January I disappear. Who am I?", "The letter 'B'"),
    ("Spot me in Square, Rhombus; you won't find me in Star, Circle. What am I?", "The letter 'U'"),
    ("I appear in Silver yet in Lead, Helium, Gold, Copper, Nitrogen, Carbon I'm gone. Who am I?", "The letter 'S'"),
    ("In Violet, Pink, Indigo I'm there; in May, March, November, July I disappear. Who am I?", "The letter 'I'"),
    ("Spot me in Rhombus; you won't find me in November, April. What am I?", "The letter 'H'"),
    ("I appear in Monkey yet in Tiger, Donkey, Wolf, Shark, Cobra, Rabbit I'm gone. Who am I?", "The letter 'M'"),
    ("I appear in Football yet in Soccer, Golf, Volleyball I'm gone. Who am I?", "The letter 'T'"),
    ("You'll find me in all of Cricket but in none of Europe, Africa. What am I?", "The letter 'K'"),
    ("You'll find me in all of Uranus, Mercury but in none of West, East, Center. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Wednesday, absent from Volleyball, Soccer, Cricket. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Football, absent from Tennis, Cricket. What am I?", "The letter 'O'"),
    ("Spot me in Jupiter, Earth; you won't find me in Mango, Pear, Lemon. What am I?", "The letter 'T'"),
    ("I appear in Plum yet in Sulfur, Lead I'm gone. Who am I?", "The letter 'M'"),
    ("In Rugby I'm there; in Cello, Harp I disappear. Who am I?", "The letter 'U'"),
    ("Spot me in Rabbit; you won't find me in Cobra, Eagle, Zebra. What am I?", "The letter 'I'"),
    ("Spot me in Harp; you won't find me in Trumpet, Guitar, Flute, Violin. What am I?", "The letter 'H'"),
    ("I'm present in every letter of Thursday, Friday, absent from Violet. What am I?", "The letter 'Y'"),
    ("In Peach, Cherry I'm there; in Plum, Lemon, Orange I disappear. Who am I?", "The letter 'H'"),
    ("You'll find me in all of East, West but in none of Plum, Kiwi. What am I?", "The letter 'E'"),
    ("I appear in Wolf yet in Cobra, Giraffe I'm gone. Who am I?", "The letter 'W'"),
    ("I'm present in every letter of South, absent from Africa, Antarctica, America, Europe. What am I?", "The letter 'H'"),
    ("I appear in Gray yet in Indigo, Black I'm gone. Who am I?", "The letter 'R'"),
    ("In Octagon, Star I'm there; in Square I disappear. Who am I?", "The letter 'T'"),
    ("Spot me in Kiwi; you won't find me in Thursday, Friday, Tuesday. What am I?", "The letter 'W'"),
    ("You'll find me in all of America but in none of Africa, Asia, Antarctica, Oceania. What am I?", "The letter 'M'"),
    ("You'll find me in all of Lemon but in none of July. What am I?", "The letter 'N'"),
    ("You'll find me in all of Basketball but in none of Center, North. What am I?", "The letter 'S'"),
    ("You'll find me in all of America but in none of Giraffe. What am I?", "The letter 'M'"),
    ("In Sunday I'm there; in Silver, Nitrogen, Sulfur, Tin I disappear. Who am I?", "The letter 'A'"),
    ("I appear in Rhombus, Oval yet in Rectangle, Square, Circle I'm gone. Who am I?", "The letter 'O'"),
    ("In Monday I'm there; in August I disappear. Who am I?", "The letter 'O'"),
    ("In Nitrogen, Oxygen I'm there; in Violin I disappear. Who am I?", "The letter 'E'"),
    ("I'm present in every letter of Sunday, Wednesday, Thursday, absent from America, Europe. What am I?", "The letter 'D'"),
    ("I appear in Pentagon yet in Circle, Octagon I'm gone. Who am I?", "The letter 'P'"),
    ("You'll find me in all of East, South, North but in none of Africa. What am I?", "The letter 'T'"),
    ("In Wolf I'm there; in Moose, Lion, Yak, Rabbit, Panda I disappear. Who am I?", "The letter 'F'"),
    ("Spot me in Pentagon; you won't find me in Octagon, Rectangle, Star. What am I?", "The letter 'P'"),
    ("You'll find me in all of Uranus but in none of Rugby, Soccer, Football, Baseball. What am I?", "The letter 'N'"),
    ("You'll find me in all of Trumpet but in none of Cello, Piano, Drum, Saxophone, Violin, Harp. What am I?", "The letter 'T'"),
    ("In Basketball I'm there; in Blue, Violet I disappear. Who am I?", "The letter 'K'"),
    ("Spot me in Hexagon; you won't find me in Octagon, Circle, Rectangle, Oval. What am I?", "The letter 'H'"),
    ("Spot me in Cricket, Hockey; you won't find me in Volleyball, Tennis. What am I?", "The letter 'K'"),
    ("I'm present in every letter of Hexagon, absent from Circle, Oval, Triangle, Square. What am I?", "The letter 'X'"),
    ("Spot me in Peach, Grape, Lime, Apple, Orange; you won't find me in Banana, Plum. What am I?", "The letter 'E'"),
    ("I appear in Lime, Orange yet in Mango, Plum I'm gone. Who am I?", "The letter 'E'"),
    ("In Eagle, Donkey, Otter I'm there; in Cobra I disappear. Who am I?", "The letter 'E'"),
    ("I appear in Golf, Football yet in Basketball, Volleyball, Cricket I'm gone. Who am I?", "The letter 'F'"),
    ("Spot me in Star; you won't find me in Hexagon, Triangle, Circle. What am I?", "The letter 'S'"),
    ("You'll find me in all of South but in none of Oxygen, Lead, Sulfur. What am I?", "The letter 'T'"),
    ("In Mars I'm there; in Wednesday I disappear. Who am I?", "The letter 'R'"),
    ("I'm present in every letter of Orange, absent from Apple. What am I?", "The letter 'N'"),
    ("In Monkey I'm there; in Donkey, Rabbit I disappear. Who am I?", "The letter 'M'"),
    ("Spot me in Black; you won't find me in Cricket, Rugby, Soccer. What am I?", "The letter 'A'"),
    ("In Monday, Wednesday, Saturday I'm there; in Rabbit, Bear, Moose, Tiger I disappear. Who am I?", "The letter 'Y'"),
    ("You'll find me in all of Basketball, Cricket but in none of Golf. What am I?", "The letter 'T'"),
    ("You'll find me in all of July, June but in none of Neptune, Mercury, Saturn. What am I?", "The letter 'J'"),
    ("You'll find me in all of Drum but in none of Harp, Piano. What am I?", "The letter 'M'"),
    ("I'm present in every letter of Donkey, absent from Moose, Yak. What am I?", "The letter 'N'"),
    ("Spot me in Cello; you won't find me in Saxophone, Drum, Violin. What am I?", "The letter 'C'"),
    ("Spot me in Pentagon, Rectangle, Star; you won't find me in Moose. What am I?", "The letter 'T'"),
    ("In Saturday, Friday I'm there; in South, West I disappear. Who am I?", "The letter 'R'"),
    ("Spot me in Mars, Venus, Saturn; you won't find me in Mango, Cherry. What am I?", "The letter 'S'"),
    ("I'm present in every letter of South, absent from Gray, Pink, Green. What am I?", "The letter 'U'"),
    ("Spot me in Yak; you won't find me in Oceania, America, Antarctica. What am I?", "The letter 'K'"),
    ("In January I'm there; in Neptune, Mars I disappear. Who am I?", "The letter 'Y'"),
    ("I'm present in every letter of Gray, absent from Blue, Red, White, Black, Violet, Green. What am I?", "The letter 'Y'"),
    ("I appear in Bear yet in Europe, Oceania, Africa, America I'm gone. Who am I?", "The letter 'B'"),
    ("In Brown I'm there; in Green, Black, Gray, Indigo I disappear. Who am I?", "The letter 'W'"),
    ("In South, East I'm there; in Venus, Mercury I disappear. Who am I?", "The letter 'T'"),
    ("In Venus, Saturn I'm there; in Zebra, Donkey I disappear. Who am I?", "The letter 'S'"),
    ("I appear in Sulfur yet in Lead, Hydrogen, Helium I'm gone. Who am I?", "The letter 'S'"),
    ("I appear in Golf yet in Volleyball, Football I'm gone. Who am I?", "The letter 'G'"),
    ("In Asia, Antarctica, Oceania, America I'm there; in North, West I disappear. Who am I?", "The letter 'A'"),
    ("I'm present in every letter of March, absent from June, April, November, September, August. What am I?", "The letter 'H'"),
    ("You'll find me in all of Wednesday, Tuesday but in none of Thursday, Friday. What am I?", "The letter 'E'"),
    ("Spot me in Monkey; you won't find me in Rabbit, Fox. What am I?", "The letter 'K'"),
    ("Spot me in Grape, Apple; you won't find me in Plum, Papaya, Kiwi. What am I?", "The letter 'E'"),
    ("In Tiger I'm there; in Pink, Orange, Green I disappear. Who am I?", "The letter 'T'"),
    ("I appear in Center, West, East yet in Uranus I'm gone. Who am I?", "The letter 'E'"),
    ("You'll find me in all of South, East, West but in none of Violet. What am I?", "The letter 'S'"),
    ("I'm present in every letter of Nitrogen, Tin, Hydrogen, Oxygen, absent from Helium, Sulfur, Lead. What am I?", "The letter 'N'"),
    ("In Football, Baseball I'm there; in Rugby, Tennis I disappear. Who am I?", "The letter 'A'"),
    ("You'll find me in all of Flute but in none of Friday, Sunday, Saturday, Monday. What am I?", "The letter 'L'"),
    ("In Sulfur I'm there; in Nitrogen, Silver, Helium, Tin, Gold I disappear. Who am I?", "The letter 'F'"),
    ("Spot me in Harp, Guitar; you won't find me in Flute. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Africa, absent from Saxophone, Piano. What am I?", "The letter 'R'"),
    ("Spot me in Bear, Otter, Donkey, Eagle; you won't find me in Cobra. What am I?", "The letter 'E'"),
    ("Spot me in Africa, Antarctica, America; you won't find me in Oceania, Asia. What am I?", "The letter 'R'"),
    ("You'll find me in all of Volleyball but in none of Cricket, Football. What am I?", "The letter 'Y'"),
    ("You'll find me in all of Fox, Otter but in none of Neptune, Jupiter. What am I?", "The letter 'O'"),
    ("You'll find me in all of Star but in none of Pentagon, Oval. What am I?", "The letter 'R'"),
    ("In Wednesday I'm there; in America, Antarctica, Europe, Africa I disappear. Who am I?", "The letter 'W'"),
    ("I'm present in every letter of Oval, absent from May, June. What am I?", "The letter 'O'"),
    ("Spot me in Tuesday; you won't find me in Lead, Sulfur, Helium. What am I?", "The letter 'Y'"),
    ("Spot me in Tiger, Donkey, Whale, Giraffe; you won't find me in Shark. What am I?", "The letter 'E'"),
    ("You'll find me in all of June, January but in none of July, October. What am I?", "The letter 'N'"),
    ("In Indigo, Orange I'm there; in Yellow, Gray, Black I disappear. Who am I?", "The letter 'N'"),
    ("In Oxygen, Iron I'm there; in Copper I disappear. Who am I?", "The letter 'N'"),
    ("I'm present in every letter of West, absent from South, North. What am I?", "The letter 'W'"),
    ("I appear in Hydrogen yet in Saturday, Thursday I'm gone. Who am I?", "The letter 'O'"),
    ("Spot me in Rectangle; you won't find me in September, January, July. What am I?", "The letter 'G'"),
    ("In Thursday, Sunday I'm there; in Rectangle, Star, Oval I disappear. Who am I?", "The letter 'D'"),
    ("I appear in Saxophone, Violin yet in Saturn I'm gone. Who am I?", "The letter 'O'"),
    ("Spot me in Lemon; you won't find me in Hexagon, Square, Oval. What am I?", "The letter 'M'"),
    ("I appear in Giraffe yet in Cricket, Tennis I'm gone. Who am I?", "The letter 'F'"),
    ("In October, September, December, February I'm there; in Jupiter I disappear. Who am I?", "The letter 'B'"),
    ("In April I'm there; in White, Yellow I disappear. Who am I?", "The letter 'R'"),
    ("I appear in Harp, Saxophone, Piano yet in Cello, Flute, Clarinet, Guitar I'm gone. Who am I?", "The letter 'P'"),
    ("I appear in Saturday yet in Sunday, Friday I'm gone. Who am I?", "The letter 'T'"),
    ("You'll find me in all of Thursday, Tuesday but in none of Sunday, Wednesday, Friday. What am I?", "The letter 'T'"),
    ("I'm present in every letter of Giraffe, Rabbit, Lion, absent from Moose, Monkey, Donkey. What am I?", "The letter 'I'"),
    ("I appear in Uranus yet in Brown, Black, Blue, Gray I'm gone. Who am I?", "The letter 'S'"),
    ("You'll find me in all of Europe but in none of Africa, Oceania. What am I?", "The letter 'P'"),
    ("You'll find me in all of Circle but in none of Zebra. What am I?", "The letter 'I'"),
    ("In February I'm there; in Papaya, Apple, Peach I disappear. Who am I?", "The letter 'U'"),
    ("Spot me in Center, South, East; you won't find me in Mercury, Mars. What am I?", "The letter 'T'"),
    ("I appear in Nitrogen, Oxygen yet in Wednesday, Tuesday I'm gone. Who am I?", "The letter 'G'"),
    ("You'll find me in all of Mars but in none of Venus, Saturn. What am I?", "The letter 'M'"),
    ("I appear in Bear, Giraffe yet in Moose I'm gone. Who am I?", "The letter 'A'"),
    ("In Hockey, Soccer I'm there; in Lime, Kiwi, Grape, Pear I disappear. Who am I?", "The letter 'O'"),
    ("You'll find me in all of Mars, Jupiter but in none of South. What am I?", "The letter 'R'"),
    ("Spot me in America, Africa, Antarctica, Oceania; you won't find me in Asia, Europe. What am I?", "The letter 'C'"),
    ("Spot me in Peach, Cherry; you won't find me in Lemon, Kiwi. What am I?", "The letter 'C'"),
    ("I appear in America, Africa, Oceania yet in Tuesday, Friday I'm gone. Who am I?", "The letter 'C'"),
    ("In Rhombus I'm there; in Circle, Star, Oval, Rectangle I disappear. Who am I?", "The letter 'B'"),
    ("In South, North, East, Center I'm there; in January I disappear. Who am I?", "The letter 'T'"),
    ("You'll find me in all of Iron but in none of Black. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Blue, absent from Black, Orange. What am I?", "The letter 'U'"),
    ("In Europe I'm there; in Antarctica, America I disappear. Who am I?", "The letter 'U'"),
    ("Spot me in Tuesday, Friday, Sunday, Saturday; you won't find me in Harp, Guitar, Flute. What am I?", "The letter 'Y'"),
    ("I'm present in every letter of Shark, absent from Harp, Drum, Trumpet. What am I?", "The letter 'K'"),
    ("In Monday, Thursday, Friday I'm there; in Guitar I disappear. Who am I?", "The letter 'D'"),
    ("I'm present in every letter of Gold, absent from Antarctica, Africa. What am I?", "The letter 'L'"),
    ("In Basketball, Soccer I'm there; in Golf I disappear. Who am I?", "The letter 'S'"),
    ("I'm present in every letter of Trumpet, Saxophone, absent from Helium, Lead. What am I?", "The letter 'P'"),
    ("In Lime I'm there; in Sulfur, Oxygen, Nitrogen I disappear. Who am I?", "The letter 'M'"),
    ("I appear in Neptune, Uranus, Venus yet in Mercury I'm gone. Who am I?", "The letter 'N'"),
    ("Spot me in West, East, South, North; you won't find me in Orange, Green, Yellow. What am I?", "The letter 'T'"),
    ("I appear in Donkey yet in March, February, July, August I'm gone. Who am I?", "The letter 'D'"),
    ("I'm present in every letter of Oceania, America, absent from Indigo, Pink, Black. What am I?", "The letter 'E'"),
    ("In Wednesday I'm there; in Saturday, Friday I disappear. Who am I?", "The letter 'N'"),
    ("Spot me in Tuesday, Saturday, Thursday; you won't find me in Wednesday. What am I?", "The letter 'T'"),
    ("In Pentagon, Octagon I'm there; in Sunday, Tuesday I disappear. Who am I?", "The letter 'G'"),
    ("You'll find me in all of Thursday, Friday, Tuesday but in none of Center, North. What am I?", "The letter 'D'"),
    ("I appear in Mercury, Earth, Venus yet in Uranus, Mars I'm gone. Who am I?", "The letter 'E'"),
    ("You'll find me in all of Africa, America, Asia, Oceania but in none of Wednesday, Thursday, Saturday. What am I?", "The letter 'I'"),
    ("You'll find me in all of America, Oceania, Asia but in none of Circle. What am I?", "The letter 'A'"),
    ("You'll find me in all of Trumpet but in none of Drum, Harp. What am I?", "The letter 'T'"),
    ("You'll find me in all of Soccer but in none of Cricket, Volleyball. What am I?", "The letter 'S'"),
    ("I appear in Grape yet in Eagle, Whale, Rabbit I'm gone. Who am I?", "The letter 'P'"),
    ("In Copper I'm there; in West, North, East I disappear. Who am I?", "The letter 'C'"),
    ("You'll find me in all of Tuesday but in none of January, February. What am I?", "The letter 'T'"),
    ("I'm present in every letter of Gray, Orange, absent from Pink. What am I?", "The letter 'G'"),
    ("You'll find me in all of Iron, Copper but in none of Tin. What am I?", "The letter 'R'"),
    ("I appear in Wolf yet in Friday I'm gone. Who am I?", "The letter 'O'"),
    ("You'll find me in all of Whale but in none of Black, Orange. What am I?", "The letter 'W'"),
    ("You'll find me in all of April but in none of Gold, Sulfur, Copper. What am I?", "The letter 'I'"),
    ("I'm present in every letter of Rhombus, Rectangle, Star, Circle, absent from Flute. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Green, absent from White, Gray. What am I?", "The letter 'N'"),
    ("You'll find me in all of Africa but in none of Oceania, Antarctica. What am I?", "The letter 'F'"),
    ("You'll find me in all of Saturday, Monday, Thursday, Sunday but in none of Otter, Cobra, Whale. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Tin, Nitrogen, absent from Carbon, Sulfur, Silver. What am I?", "The letter 'T'"),
    ("I'm present in every letter of Copper, Hydrogen, absent from Gold. What am I?", "The letter 'E'"),
    ("You'll find me in all of Earth, Jupiter, Venus but in none of South. What am I?", "The letter 'E'"),
    ("You'll find me in all of June but in none of Cricket, Volleyball. What am I?", "The letter 'J'"),
    ("In Pink I'm there; in Brown, Red, Green, Violet, Indigo I disappear. Who am I?", "The letter 'K'"),
    ("Spot me in Rectangle, Square, Pentagon, Triangle; you won't find me in Jupiter. What am I?", "The letter 'A'"),
    ("In Pink I'm there; in Red, Violet, Brown, White, Blue I disappear. Who am I?", "The letter 'P'"),
    ("I'm present in every letter of Sunday, Wednesday, absent from Tuesday, Thursday. What am I?", "The letter 'N'"),
    ("Spot me in Cello, Piano; you won't find me in Clarinet. What am I?", "The letter 'O'"),
    ("You'll find me in all of Saturday, Monday but in none of Oval. What am I?", "The letter 'Y'"),
    ("I appear in Tin yet in Carbon, Silver, Gold, Helium, Sulfur, Copper I'm gone. Who am I?", "The letter 'T'"),
    ("I'm present in every letter of Pentagon, absent from Rhombus, Octagon. What am I?", "The letter 'E'"),
    ("I appear in Venus, Mercury, Earth, Neptune yet in Mars I'm gone. Who am I?", "The letter 'E'"),
    ("I appear in Antarctica, Asia, Africa, America, Oceania yet in Europe I'm gone. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Clarinet, absent from Pink, Violet, Black. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Cherry, absent from Plum, Lime, Mango. What am I?", "The letter 'C'"),
    ("You'll find me in all of Guitar but in none of Tin. What am I?", "The letter 'G'"),
    ("In Peach I'm there; in Papaya, Grape I disappear. Who am I?", "The letter 'H'"),
    ("You'll find me in all of Peach, Plum but in none of Mango. What am I?", "The letter 'P'"),
    ("Spot me in Grape, Pear, Peach; you won't find me in Zebra, Whale, Shark, Bear. What am I?", "The letter 'P'"),
    ("I appear in Clarinet, Cello yet in Oceania, America I'm gone. Who am I?", "The letter 'L'"),
    ("In Circle I'm there; in Hexagon, Rectangle, Octagon I disappear. Who am I?", "The letter 'I'"),
    ("You'll find me in all of Pentagon, Rectangle but in none of Nitrogen, Sulfur, Iron. What am I?", "The letter 'A'"),
    ("In Pear I'm there; in Papaya, Peach, Banana I disappear. Who am I?", "The letter 'R'"),
    ("In Tennis I'm there; in Football, Baseball I disappear. Who am I?", "The letter 'N'"),
    ("In Thursday, Sunday, Friday I'm there; in June I disappear. Who am I?", "The letter 'Y'"),
    ("In Whale, Shark I'm there; in Tuesday, Wednesday I disappear. Who am I?", "The letter 'H'"),
    ("In Friday I'm there; in Monday, Sunday, Thursday, Wednesday, Tuesday, Saturday I disappear. Who am I?", "The letter 'F'"),
    ("I appear in Iron yet in Drum, Flute I'm gone. Who am I?", "The letter 'O'"),
    ("Spot me in Oval, Octagon; you won't find me in Rhombus. What am I?", "The letter 'A'"),
    ("You'll find me in all of Volleyball but in none of Tennis, Cricket, Rugby. What am I?", "The letter 'V'"),
    ("You'll find me in all of Saturday, Friday but in none of Sunday. What am I?", "The letter 'R'"),
    ("You'll find me in all of Basketball, Football, Volleyball but in none of Friday. What am I?", "The letter 'L'"),
    ("I appear in Banana yet in Lemon, Lime I'm gone. Who am I?", "The letter 'A'"),
    ("Spot me in America; you won't find me in Antarctica, Oceania. What am I?", "The letter 'M'"),
    ("Spot me in Clarinet; you won't find me in Oceania, Asia. What am I?", "The letter 'L'"),
    ("I'm present in every letter of Hexagon, Triangle, Square, absent from Cherry. What am I?", "The letter 'A'"),
    ("I'm present in every letter of Trumpet, Guitar, absent from Black, Pink. What am I?", "The letter 'T'"),
    ("You'll find me in all of Friday but in none of Thursday, Saturday. What am I?", "The letter 'F'"),
    ("I'm present in every letter of Europe, Antarctica, Africa, absent from Basketball. What am I?", "The letter 'R'"),
    ("I appear in Monday, Saturday, Sunday, Wednesday yet in Giraffe, Moose, Panda, Cobra I'm gone. Who am I?", "The letter 'Y'"),
    ("I appear in Europe yet in America, Africa, Antarctica, Asia I'm gone. Who am I?", "The letter 'P'"),
    ("Spot me in America, Africa, Antarctica, Asia; you won't find me in Orange. What am I?", "The letter 'I'"),
    ("You'll find me in all of Carbon but in none of November, July. What am I?", "The letter 'A'"),
    ("You'll find me in all of North, South but in none of Silver, Copper. What am I?", "The letter 'T'"),
    ("In Wednesday I'm there; in Friday, Sunday I disappear. Who am I?", "The letter 'E'"),
    ("You'll find me in all of Pentagon, Hexagon, Octagon, Rhombus but in none of Star, Square. What am I?", "The letter 'O'"),
    ("You'll find me in all of Orange but in none of Thursday. What am I?", "The letter 'O'"),
    ("You'll find me in all of Oceania but in none of Europe, America. What am I?", "The letter 'N'"),
    ("I'm present in every letter of February, absent from Asia, Europe, Antarctica, Oceania. What am I?", "The letter 'B'"),
    ("I appear in Basketball, Tennis, Baseball yet in Banana I'm gone. Who am I?", "The letter 'S'"),
    ("I'm present in every letter of Golf, absent from July, March, June. What am I?", "The letter 'G'"),
    ("I appear in Tuesday, Friday, Wednesday yet in Lime, Grape, Pear, Lemon I'm gone. Who am I?", "The letter 'Y'"),
    ("Spot me in Venus, Mercury, Jupiter; you won't find me in Violet, Gray. What am I?", "The letter 'U'"),
    ("I'm present in every letter of October, absent from Orange, Green. What am I?", "The letter 'C'"),
    ("I appear in Venus yet in Mercury, Mars I'm gone. Who am I?", "The letter 'V'"),
    ("You'll find me in all of Center, East, West but in none of Europe. What am I?", "The letter 'T'"),
    ("I appear in Friday yet in Tuesday, Wednesday, Monday, Sunday, Saturday I'm gone. Who am I?", "The letter 'F'"),
    ("I'm present in every letter of Sulfur, Iron, absent from Mango, Banana. What am I?", "The letter 'R'"),
    ("You'll find me in all of Golf, Rugby but in none of Cricket, Soccer. What am I?", "The letter 'G'"),
    ("I appear in Monday, Thursday, Tuesday yet in Square I'm gone. Who am I?", "The letter 'D'"),
    ("I appear in West yet in Center, South, North I'm gone. Who am I?", "The letter 'W'"),
    ("In Pentagon, Oval I'm there; in Circle I disappear. Who am I?", "The letter 'A'"),
    ("You'll find me in all of Baseball but in none of Soccer, Rugby. What am I?", "The letter 'A'"),
    ("I appear in Wednesday, Monday, Tuesday, Saturday yet in Cello, Guitar, Drum, Piano I'm gone. Who am I?", "The letter 'Y'"),
    ("You'll find me in all of Gold but in none of Tin, Carbon, Copper, Nitrogen. What am I?", "The letter 'L'"),
    ("I appear in South yet in Hockey, Rugby, Volleyball I'm gone. Who am I?", "The letter 'T'"),
    ("In Silver, Lead I'm there; in Gold I disappear. Who am I?", "The letter 'E'"),
    ("I'm present in every letter of Nitrogen, Carbon, absent from Lead, Oxygen. What am I?", "The letter 'R'"),
    ("I appear in Rugby yet in Baseball, Football I'm gone. Who am I?", "The letter 'G'"),
    ("I appear in Copper yet in Sulfur, Oxygen, Nitrogen, Lead I'm gone. Who am I?", "The letter 'P'"),
    ("Spot me in Thursday, Wednesday, Tuesday; you won't find me in Green, Gray, Yellow, White. What am I?", "The letter 'S'"),
    ("Spot me in Saxophone, Clarinet, Piano, Guitar; you won't find me in Flute, Trumpet, Cello. What am I?", "The letter 'A'"),
    ("I'm present in every letter of Oceania, absent from Asia, America, Africa, Antarctica. What am I?", "The letter 'O'"),
    ("I'm present in every letter of May, absent from June, February. What am I?", "The letter 'M'"),
    ("Spot me in Gold, Lead; you won't find me in America, Oceania, Antarctica. What am I?", "The letter 'D'"),
    ("I appear in Rabbit yet in Thursday I'm gone. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Jupiter, absent from Earth, Venus. What am I?", "The letter 'J'"),
    ("In Sunday, Wednesday, Saturday I'm there; in Oceania I disappear. Who am I?", "The letter 'S'"),
    ("Spot me in Saturn, Uranus; you won't find me in Neptune. What am I?", "The letter 'A'"),
    ("In Hockey, Volleyball, Basketball I'm there; in Rugby I disappear. Who am I?", "The letter 'E'"),
    ("In Africa I'm there; in Lemon I disappear. Who am I?", "The letter 'R'"),
    ("Spot me in North, Center; you won't find me in South, East, West. What am I?", "The letter 'R'"),
    ("I appear in Tiger, Rabbit yet in Wolf I'm gone. Who am I?", "The letter 'R'"),
    ("You'll find me in all of Pink, Indigo but in none of Green. What am I?", "The letter 'I'"),
    ("In Orange, Gray I'm there; in West, East I disappear. Who am I?", "The letter 'R'"),
    ("In Harp, Saxophone, Piano, Clarinet I'm there; in Trumpet I disappear. Who am I?", "The letter 'A'"),
    ("Spot me in Mercury, Uranus; you won't find me in September. What am I?", "The letter 'U'"),
    ("Spot me in Oceania, Antarctica; you won't find me in Asia, Europe, Africa. What am I?", "The letter 'N'"),
    ("You'll find me in all of September but in none of October, January. What am I?", "The letter 'S'"),
    ("I'm present in every letter of Apple, absent from Baseball, Volleyball, Tennis, Cricket. What am I?", "The letter 'P'"),
    ("I appear in Basketball, Football yet in Black, Red, Gray I'm gone. Who am I?", "The letter 'T'"),
    ("I'm present in every letter of Iron, Nitrogen, Hydrogen, absent from Silver. What am I?", "The letter 'O'"),
    ("I appear in Africa yet in Antarctica, Europe, Asia, Oceania, America I'm gone. Who am I?", "The letter 'F'"),
    ("Spot me in Mars, Earth, Saturn; you won't find me in Jupiter, Neptune, Mercury. What am I?", "The letter 'A'"),
    ("In Gold, Helium I'm there; in Mars I disappear. Who am I?", "The letter 'L'"),
    ("Spot me in Saturday; you won't find me in Rectangle, Pentagon, Circle. What am I?", "The letter 'D'"),
    ("I appear in Golf yet in Papaya I'm gone. Who am I?", "The letter 'G'"),
    ("I appear in Neptune, Earth yet in Orange, Gray I'm gone. Who am I?", "The letter 'T'"),
    ("I appear in Asia, America, Antarctica, Oceania yet in Neptune I'm gone. Who am I?", "The letter 'I'"),
    ("Spot me in Violin, Guitar; you won't find me in Flute, Saxophone. What am I?", "The letter 'I'"),
    ("In Oxygen I'm there; in North, Center I disappear. Who am I?", "The letter 'X'"),
    ("In Sulfur I'm there; in Volleyball, Golf, Cricket, Football I disappear. Who am I?", "The letter 'U'"),
    ("You'll find me in all of North but in none of Pink, Green, Brown, Yellow. What am I?", "The letter 'H'"),
    ("You'll find me in all of Volleyball but in none of Rugby, Baseball. What am I?", "The letter 'O'"),
]

def normalize_text(text):
    """Normalize text for comparison by removing punctuation, extra spaces, and converting to lowercase"""
    # Remove punctuation and convert to lowercase
    text = text.translate(str.maketrans('', '', string.punctuation)).lower()
    # Remove extra whitespace and normalize spaces
    text = ' '.join(text.split())
    return text

def check_duplicates_in_batch(riddles):
    """Check for duplicates within the batch"""
    seen_questions = {}
    seen_answers = {}
    duplicates = []

    for i, (question, answer) in enumerate(riddles):
        norm_q = normalize_text(question)
        norm_a = normalize_text(answer)

        # Check question duplicates
        if norm_q in seen_questions:
            duplicates.append(f"  Items {i} and {seen_questions[norm_q]} have same question: {question[:50]}...")
        else:
            seen_questions[norm_q] = i

        # Check answer duplicates
        if norm_a in seen_answers:
            duplicates.append(f"  Items {i} and {seen_answers[norm_a]} have same answer: {answer[:50]}...")
        else:
            seen_answers[norm_a] = i

    return duplicates

def categorize_difficulty(question, answer):
    """Auto-categorize riddle difficulty based on complexity"""
    q_len = len(question)
    a_len = len(answer)

    # Count complex indicators
    complex_words = ['present', 'absent', 'appear', 'disappear', 'find me in all', 'none of']
    complexity_score = sum(1 for word in complex_words if word in question.lower())

    # Letter-based riddles are typically harder
    if "letter" in answer.lower() or "spot me" in question.lower():
        return "hard"

    # Short answers with simple language are usually easy
    if a_len < 15 and complexity_score == 0 and q_len < 80:
        return "easy"

    # Complex word-based riddles or longer questions are hard
    if complexity_score > 0 or q_len > 120:
        return "hard"

    # Everything else is medium
    return "medium"

def generate_hint(question, answer):
    """Generate an appropriate hint for the riddle"""
    if "letter" in answer.lower():
        return f"Think about the alphabet and what letters appear in certain words."
    elif answer.lower() in ['a piano', 'piano']:
        return "Think about musical instruments with keys."
    elif answer.lower() in ['a book', 'book']:
        return "Something you read that has many leaves but isn't a plant."
    elif answer.lower() in ['a clock', 'clock']:
        return "It tells time and has hands but no arms."
    else:
        # Generic hints based on answer type
        if any(word in answer.lower() for word in ['a ', 'an ']):
            return f"Think about objects that {question.split('?')[0].lower().replace('what', '').replace('i am', 'are').strip()}."
        else:
            return f"The answer is a single word or concept."

def add_riddles_to_db():
    """Add new riddles to the database with duplicate checking"""

    print("Checking for duplicates within the new riddle batch...")

    # Check for duplicates within the new batch
    batch_duplicates = check_duplicates_in_batch(riddles_batch2)
    if batch_duplicates:
        print(f"WARNING: Found {len(batch_duplicates)} potential duplicates in batch:")
        for dup in batch_duplicates[:10]:  # Show first 10
            print(dup)
        if len(batch_duplicates) > 10:
            print(f"  ... and {len(batch_duplicates) - 10} more")

    # Connect to database and get existing riddles
    conn = sqlite3.connect('riddles.db')
    cursor = conn.cursor()

    # Get all existing riddles for duplicate checking
    cursor.execute("SELECT question, answer FROM riddles")
    existing_riddles = cursor.fetchall()
    print(f"Found {len(existing_riddles)} existing riddles in database")

    # Normalize existing riddles for comparison
    existing_normalized = set()
    for q, a in existing_riddles:
        norm_q = normalize_text(q)
        norm_a = normalize_text(a)
        existing_normalized.add((norm_q, norm_a))

    # Process new riddles
    added_count = 0
    skipped_duplicates = 0

    for i, (question, answer) in enumerate(riddles_batch2):
        # Normalize for duplicate checking
        norm_question = normalize_text(question)
        norm_answer = normalize_text(answer)

        # Check if this riddle already exists in database
        if (norm_question, norm_answer) in existing_normalized:
            print(f"SKIP DB duplicate #{i}: {question[:50]}...")
            skipped_duplicates += 1
            continue

        # Categorize difficulty and generate hint
        difficulty = categorize_difficulty(question, answer)
        hint = generate_hint(question, answer)

        # Insert into database
        cursor.execute("""
            INSERT INTO riddles (question, answer, hint, difficulty)
            VALUES (?, ?, ?, ?)
        """, (question, answer, hint, difficulty))

        print(f"ADDED [{difficulty}]: {question[:50]}...")
        added_count += 1

        # Add to existing set to prevent duplicates within this batch
        existing_normalized.add((norm_question, norm_answer))

    # Commit changes
    conn.commit()
    conn.close()

    print(f"\nSUMMARY:")
    print(f"- Total riddles in batch: {len(riddles_batch2)}")
    print(f"- Added to database: {added_count}")
    print(f"- Skipped (duplicates): {skipped_duplicates}")
    print(f"- Batch duplicates found: {len(batch_duplicates)}")

if __name__ == "__main__":
    add_riddles_to_db()