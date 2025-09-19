#!/usr/bin/env python3
import sqlite3
import re
import string

# New riddles batch 3
riddles_batch3 = [
    ("In Baseball I'm there; in Oxygen, Tin I disappear. Who am I?", "The letter 'S'"),
    ("You'll find me in all of February, August, June, January but in none of May, November, April. What am I?", "The letter 'U'"),
    ("You'll find me in all of Red, Violet but in none of Indigo. What am I?", "The letter 'E'"),
    ("I'm present in every letter of Monday, Tuesday, Sunday, absent from Eagle, Giraffe, Yak, Moose. What am I?", "The letter 'D'"),
    ("Spot me in Tuesday, Sunday; you won't find me in Gray, White, Pink, Indigo. What am I?", "The letter 'U'"),
    ("You'll find me in all of Africa but in none of Cello, Clarinet. What am I?", "The letter 'F'"),
    ("I'm present in every letter of West, absent from Rhombus, Octagon. What am I?", "The letter 'W'"),
    ("I'm present in every letter of Circle, Rectangle, absent from Uranus, Mercury, Neptune, Mars. What am I?", "The letter 'L'"),
    ("You'll find me in all of Jupiter but in none of Saturn, Mars. What am I?", "The letter 'E'"),
    ("Spot me in Bear, Giraffe; you won't find me in Lion. What am I?", "The letter 'R'"),
    ("Spot me in Eagle; you won't find me in Rabbit, Bear, Monkey, Whale. What am I?", "The letter 'G'"),
    ("I appear in Copper yet in Nitrogen, Silver, Iron, Tin I'm gone. Who am I?", "The letter 'C'"),
    ("I appear in Volleyball yet in Hockey, Soccer, Cricket I'm gone. Who am I?", "The letter 'L'"),
    ("You'll find me in all of June but in none of Venus. What am I?", "The letter 'J'"),
    ("I appear in Copper, Hydrogen yet in Octagon, Star I'm gone. Who am I?", "The letter 'E'"),
    ("In Europe, Oceania I'm there; in Antarctica, America, Asia I disappear. Who am I?", "The letter 'O'"),
    ("Spot me in Lead; you won't find me in Oxygen, Silver, Sulfur, Nitrogen, Helium. What am I?", "The letter 'A'"),
    ("Spot me in November; you won't find me in Violin. What am I?", "The letter 'R'"),
    ("Spot me in Baseball; you won't find me in Earth, Saturn, Mercury, Mars. What am I?", "The letter 'B'"),
    ("I'm present in every letter of Oval, absent from Grape. What am I?", "The letter 'V'"),
    ("I'm present in every letter of Africa, absent from Pentagon, Hexagon, Rhombus, Rectangle. What am I?", "The letter 'F'"),
    ("I appear in March yet in Mars, Neptune I'm gone. Who am I?", "The letter 'C'"),
    ("I appear in Guitar, Saxophone yet in Drum, Flute, Cello I'm gone. Who am I?", "The letter 'A'"),
    ("In Sunday, Tuesday, Friday I'm there; in Saturn, Jupiter, Neptune I disappear. Who am I?", "The letter 'D'"),
    ("In Circle I'm there; in Rugby I disappear. Who am I?", "The letter 'E'"),
    ("You'll find me in all of Triangle but in none of Rhombus, Oval. What am I?", "The letter 'I'"),
    ("I'm present in every letter of Violet, absent from Orange, Pink, Black, Brown. What am I?", "The letter 'V'"),
    ("I appear in Friday yet in Lemon, Banana I'm gone. Who am I?", "The letter 'Y'"),
    ("You'll find me in all of Basketball but in none of Baseball, Football, Golf, Soccer. What am I?", "The letter 'K'"),
    ("You'll find me in all of February, December, June but in none of Sunday. What am I?", "The letter 'E'"),
    ("I appear in July yet in Africa, Antarctica I'm gone. Who am I?", "The letter 'L'"),
    ("You'll find me in all of Hydrogen but in none of Thursday, Wednesday. What am I?", "The letter 'G'"),
    ("Spot me in Mars; you won't find me in Earth, Neptune, Jupiter. What am I?", "The letter 'S'"),
    ("You'll find me in all of Drum but in none of North, South. What am I?", "The letter 'D'"),
    ("I appear in North, Center, South yet in February I'm gone. Who am I?", "The letter 'T'"),
    ("Spot me in South, Center, West; you won't find me in Carbon, Iron, Silver, Oxygen. What am I?", "The letter 'T'"),
    ("You'll find me in all of Oxygen, Hydrogen, Lead but in none of Panda. What am I?", "The letter 'E'"),
    ("In Kiwi, Lime I'm there; in Earth, Mercury I disappear. Who am I?", "The letter 'I'"),
    ("You'll find me in all of Volleyball, Baseball but in none of Hockey. What am I?", "The letter 'A'"),
    ("You'll find me in all of August but in none of Oceania, Africa. What am I?", "The letter 'S'"),
    ("Spot me in Pentagon; you won't find me in Hexagon, Triangle, Star. What am I?", "The letter 'P'"),
    ("I'm present in every letter of Jupiter, Mercury, absent from Donkey, Wolf. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Baseball, Rugby, absent from Guitar, Clarinet. What am I?", "The letter 'B'"),
    ("I appear in Friday, Sunday, Saturday, Monday yet in Copper, Tin, Nitrogen, Iron I'm gone. Who am I?", "The letter 'D'"),
    ("In Monday, Wednesday I'm there; in Tuesday I disappear. Who am I?", "The letter 'N'"),
    ("Spot me in December, September; you won't find me in March. What am I?", "The letter 'E'"),
    ("In Tin I'm there; in Uranus I disappear. Who am I?", "The letter 'I'"),
    ("Spot me in Jupiter, Saturn; you won't find me in Plum, Cherry, Lemon, Orange. What am I?", "The letter 'T'"),
    ("I appear in Shark, Monkey yet in Tiger, Zebra I'm gone. Who am I?", "The letter 'K'"),
    ("Spot me in Piano; you won't find me in Wolf, Moose, Otter. What am I?", "The letter 'P'"),
    ("In Antarctica, Asia, Africa, America I'm there; in West, South, North I disappear. Who am I?", "The letter 'I'"),
    ("In Circle, Octagon I'm there; in Fox I disappear. Who am I?", "The letter 'C'"),
    ("Spot me in Cello; you won't find me in Piano, Violin, Guitar. What am I?", "The letter 'C'"),
    ("In Friday, Wednesday I'm there; in Flute, Saxophone, Piano I disappear. Who am I?", "The letter 'Y'"),
    ("I appear in Black yet in White, Yellow, Red I'm gone. Who am I?", "The letter 'K'"),
    ("I'm present in every letter of Saturday, absent from Basketball, Hockey, Cricket, Baseball. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Center, absent from North, East, South. What am I?", "The letter 'C'"),
    ("In Friday I'm there; in Drum I disappear. Who am I?", "The letter 'I'"),
    ("In Donkey I'm there; in Hydrogen, Carbon, Silver I disappear. Who am I?", "The letter 'K'"),
    ("In Jupiter I'm there; in July, August, January I disappear. Who am I?", "The letter 'I'"),
    ("I appear in Moose yet in Silver, Tin, Oxygen, Copper I'm gone. Who am I?", "The letter 'M'"),
    ("In Cherry, Grape I'm there; in Gold I disappear. Who am I?", "The letter 'R'"),
    ("I'm present in every letter of Shark, absent from Fox, Monkey, Donkey, Whale. What am I?", "The letter 'R'"),
    ("I'm present in every letter of North, absent from East, South. What am I?", "The letter 'N'"),
    ("In Asia, Africa, Oceania I'm there; in Europe I disappear. Who am I?", "The letter 'A'"),
    ("I'm present in every letter of Sulfur, Silver, absent from Banana. What am I?", "The letter 'S'"),
    ("I appear in Tuesday yet in Green, Gray I'm gone. Who am I?", "The letter 'D'"),
    ("I appear in Silver yet in Helium, Sulfur, Oxygen I'm gone. Who am I?", "The letter 'V'"),
    ("I'm present in every letter of Oceania, Antarctica, America, Africa, absent from Helium. What am I?", "The letter 'A'"),
    ("In Cricket I'm there; in Tennis, Basketball, Baseball I disappear. Who am I?", "The letter 'C'"),
    ("Spot me in Donkey; you won't find me in Moose, Cobra, Whale, Bear, Tiger, Otter. What am I?", "The letter 'K'"),
    ("In Guitar, Clarinet I'm there; in Harp, Saxophone I disappear. Who am I?", "The letter 'I'"),
    ("I appear in Football, Volleyball yet in Hexagon, Pentagon, Triangle I'm gone. Who am I?", "The letter 'B'"),
    ("Spot me in Volleyball, Golf; you won't find me in Monkey, Otter, Giraffe. What am I?", "The letter 'L'"),
    ("You'll find me in all of Papaya but in none of Square, Circle. What am I?", "The letter 'P'"),
    ("Spot me in Trumpet; you won't find me in Drum, Guitar. What am I?", "The letter 'P'"),
    ("You'll find me in all of Sulfur but in none of February, August, January. What am I?", "The letter 'L'"),
    ("I appear in Zebra yet in Cello, Harp, Guitar I'm gone. Who am I?", "The letter 'Z'"),
    ("I appear in February yet in Mars, Mercury, Venus I'm gone. Who am I?", "The letter 'F'"),
    ("I'm present in every letter of Oval, absent from November, July. What am I?", "The letter 'A'"),
    ("I'm present in every letter of Square, absent from Iron, Lead, Gold, Carbon. What am I?", "The letter 'S'"),
    ("I'm present in every letter of Piano, Guitar, Clarinet, absent from Harp. What am I?", "The letter 'I'"),
    ("In Banana I'm there; in Cherry, Apple I disappear. Who am I?", "The letter 'B'"),
    ("In Flute I'm there; in Violin, Trumpet I disappear. Who am I?", "The letter 'F'"),
    ("I'm present in every letter of Thursday, absent from Panda. What am I?", "The letter 'S'"),
    ("Spot me in Zebra; you won't find me in Otter, Shark, Donkey, Tiger, Yak. What am I?", "The letter 'B'"),
    ("Spot me in East, West, North, Center; you won't find me in Piano. What am I?", "The letter 'T'"),
    ("I appear in Tuesday, Saturday, Thursday yet in Monday I'm gone. Who am I?", "The letter 'S'"),
    ("Spot me in August; you won't find me in January, May, June, December. What am I?", "The letter 'T'"),
    ("In Lead I'm there; in Africa, Oceania I disappear. Who am I?", "The letter 'L'"),
    ("I appear in Antarctica yet in America, Africa I'm gone. Who am I?", "The letter 'T'"),
    ("Spot me in Lead, Gold; you won't find me in March, September, December. What am I?", "The letter 'L'"),
    ("You'll find me in all of November, February but in none of Center. What am I?", "The letter 'B'"),
    ("Spot me in Cricket; you won't find me in Wednesday, Tuesday, Thursday, Friday. What am I?", "The letter 'K'"),
    ("I'm present in every letter of Monday, Wednesday, Friday, absent from Square, Star. What am I?", "The letter 'D'"),
    ("Spot me in Cello; you won't find me in Saxophone, Flute, Harp. What am I?", "The letter 'C'"),
    ("In Volleyball, Soccer, Football, Hockey I'm there; in Friday, Saturday, Tuesday I disappear. Who am I?", "The letter 'O'"),
    ("Spot me in Drum; you won't find me in Venus, Mercury, Uranus. What am I?", "The letter 'D'"),
    ("Spot me in Piano, Trumpet; you won't find me in Violin. What am I?", "The letter 'P'"),
    ("In Iron, Silver, Nitrogen I'm there; in Grape, Plum I disappear. Who am I?", "The letter 'I'"),
    ("In Hexagon I'm there; in Rhombus, Rectangle, Octagon I disappear. Who am I?", "The letter 'X'"),
    ("In Golf I'm there; in Baseball, Volleyball, Hockey, Cricket, Tennis I disappear. Who am I?", "The letter 'F'"),
    ("Spot me in Venus; you won't find me in Mars, Uranus, Mercury. What am I?", "The letter 'V'"),
    ("Spot me in Silver; you won't find me in Lead, Tin. What am I?", "The letter 'R'"),
    ("You'll find me in all of Green but in none of Indigo, Violet. What am I?", "The letter 'R'"),
    ("You'll find me in all of Eagle, Giraffe but in none of Otter. What am I?", "The letter 'G'"),
    ("I'm present in every letter of North, Center, absent from South, West. What am I?", "The letter 'R'"),
    ("I appear in Center, East yet in North I'm gone. Who am I?", "The letter 'E'"),
    ("You'll find me in all of South but in none of West, North. What am I?", "The letter 'U'"),
    ("In South, West, East I'm there; in Center, North I disappear. Who am I?", "The letter 'S'"),
    ("I appear in Earth, Jupiter, Neptune yet in Venus, Mars I'm gone. Who am I?", "The letter 'T'"),
    ("Spot me in Triangle; you won't find me in Peach. What am I?", "The letter 'T'"),
    ("In Thursday, Tuesday, Sunday, Saturday I'm there; in Monday, Wednesday I disappear. Who am I?", "The letter 'U'"),
    ("You'll find me in all of West but in none of East, North, Center, South. What am I?", "The letter 'W'"),
    ("I'm present in every letter of Cricket, absent from Football, Golf, Rugby, Volleyball, Tennis, Soccer. What am I?", "The letter 'K'"),
    ("You'll find me in all of Red, Orange but in none of Cello, Violin, Saxophone. What am I?", "The letter 'R'"),
    ("In Cricket I'm there; in Volleyball, Soccer I disappear. Who am I?", "The letter 'T'"),
    ("Spot me in Donkey; you won't find me in April. What am I?", "The letter 'N'"),
    ("In Jupiter, Earth, Venus I'm there; in Gray, Brown, Indigo I disappear. Who am I?", "The letter 'E'"),
    ("I'm present in every letter of Tennis, Basketball, absent from Orange, Cherry, Apple, Grape. What am I?", "The letter 'T'"),
    ("In Star, Rectangle, Hexagon I'm there; in Trumpet I disappear. Who am I?", "The letter 'A'"),
    ("I'm present in every letter of Hexagon, Rectangle, Triangle, Pentagon, Square, absent from Circle. What am I?", "The letter 'A'"),
    ("I'm present in every letter of Soccer, Volleyball, Cricket, absent from Rugby. What am I?", "The letter 'E'"),
    ("In Orange, Green I'm there; in Gray, Pink I disappear. Who am I?", "The letter 'E'"),
    ("I'm present in every letter of Brown, absent from Yellow, Orange. What am I?", "The letter 'B'"),
    ("In Jupiter I'm there; in Indigo, Green, Yellow I disappear. Who am I?", "The letter 'P'"),
    ("Spot me in February; you won't find me in Giraffe, Bear. What am I?", "The letter 'U'"),
    ("I'm present in every letter of America, Asia, Oceania, Africa, absent from Europe. What am I?", "The letter 'I'"),
    ("Spot me in Guitar, Trumpet, Drum; you won't find me in Monday. What am I?", "The letter 'R'"),
    ("I'm present in every letter of October, February, absent from June. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Pink, absent from Orange, Green, Black. What am I?", "The letter 'P'"),
    ("I'm present in every letter of Center, West, East, North, absent from Plum, Banana. What am I?", "The letter 'T'"),
    ("I appear in Soccer, Cricket yet in Lion, Cobra I'm gone. Who am I?", "The letter 'E'"),
    ("In Indigo I'm there; in South I disappear. Who am I?", "The letter 'D'"),
    ("I appear in November, October yet in May, August I'm gone. Who am I?", "The letter 'B'"),
    ("Spot me in June, July; you won't find me in December, February, October, September. What am I?", "The letter 'J'"),
    ("I'm present in every letter of Bear, absent from Lion, Shark, Wolf. What am I?", "The letter 'E'"),
    ("I'm present in every letter of Zebra, absent from Panda, Lion, Shark. What am I?", "The letter 'E'"),
    ("I appear in April yet in May, August, September, November, January I'm gone. Who am I?", "The letter 'I'"),
    ("Spot me in Orange, Peach, Pear; you won't find me in Iron, Nitrogen, Tin, Gold. What am I?", "The letter 'A'"),
    ("I appear in Tennis yet in Football, Baseball I'm gone. Who am I?", "The letter 'N'"),
    ("Spot me in February; you won't find me in Kiwi, Lemon, Orange. What am I?", "The letter 'Y'"),
    ("You'll find me in all of Sunday, Saturday, Friday but in none of Mars, Uranus, Neptune, Jupiter. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Mercury, absent from Venus, Jupiter. What am I?", "The letter 'M'"),
    ("I'm present in every letter of Friday, Tuesday, Saturday, absent from Tin, Carbon, Sulfur, Iron. What am I?", "The letter 'Y'"),
    ("In Orange, Red I'm there; in Baseball, Hockey, Tennis, Basketball I disappear. Who am I?", "The letter 'R'"),
    ("In Mercury I'm there; in Uranus, Mars I disappear. Who am I?", "The letter 'E'"),
    ("In East I'm there; in North, West I disappear. Who am I?", "The letter 'A'"),
    ("In Pear I'm there; in Mango, Orange I disappear. Who am I?", "The letter 'P'"),
    ("Spot me in East; you won't find me in Friday, Saturday. What am I?", "The letter 'E'"),
    ("Spot me in Africa; you won't find me in September, May, November. What am I?", "The letter 'F'"),
    ("I'm present in every letter of Asia, absent from Europe, Africa. What am I?", "The letter 'S'"),
    ("Spot me in Basketball, Rugby; you won't find me in Soccer. What am I?", "The letter 'B'"),
    ("You'll find me in all of Mars but in none of Saturday, Tuesday. What am I?", "The letter 'M'"),
    ("I'm present in every letter of Pentagon, absent from Clarinet, Guitar. What am I?", "The letter 'P'"),
    ("I appear in Kiwi yet in Monday I'm gone. Who am I?", "The letter 'K'"),
    ("I'm present in every letter of Copper, Gold, Iron, absent from Shark, Yak, Eagle. What am I?", "The letter 'O'"),
    ("You'll find me in all of Octagon but in none of Square, Rhombus. What am I?", "The letter 'G'"),
    ("In Yellow I'm there; in Uranus, Jupiter, Venus I disappear. Who am I?", "The letter 'L'"),
    ("I'm present in every letter of Moose, Wolf, absent from Sulfur, Lead. What am I?", "The letter 'O'"),
    ("I appear in Venus, Jupiter, Saturn, Uranus yet in Baseball I'm gone. Who am I?", "The letter 'U'"),
    ("You'll find me in all of Uranus but in none of July, April, May, January. What am I?", "The letter 'S'"),
    ("I appear in Football yet in Hockey, Golf I'm gone. Who am I?", "The letter 'A'"),
    ("I'm present in every letter of North, Center, absent from Uranus, Mars. What am I?", "The letter 'T'"),
    ("I appear in Cello yet in Saxophone, Guitar I'm gone. Who am I?", "The letter 'L'"),
    ("I appear in Octagon yet in Cricket, Golf, Football I'm gone. Who am I?", "The letter 'N'"),
    ("I appear in Friday, Monday, Saturday, Tuesday yet in Volleyball, Cricket, Hockey, Tennis I'm gone. Who am I?", "The letter 'D'"),
    ("I'm present in every letter of Venus, Saturn, absent from Neptune. What am I?", "The letter 'S'"),
    ("You'll find me in all of Violet, Indigo but in none of Green, Orange, Red. What am I?", "The letter 'I'"),
    ("I'm present in every letter of Whale, absent from Brown, Black, Red, Orange. What am I?", "The letter 'H'"),
    ("I appear in West, South yet in America, Europe I'm gone. Who am I?", "The letter 'T'"),
    ("I appear in Pentagon yet in Rhombus, Rectangle I'm gone. Who am I?", "The letter 'P'"),
    ("Spot me in Friday, Thursday, Tuesday; you won't find me in East. What am I?", "The letter 'Y'"),
    ("You'll find me in all of Saturday, Wednesday, Friday but in none of Hockey. What am I?", "The letter 'A'"),
    ("You'll find me in all of Monday but in none of Soccer. What am I?", "The letter 'N'"),
    ("You'll find me in all of Silver but in none of Carbon, Helium. What am I?", "The letter 'S'"),
    ("I'm present in every letter of Oceania, absent from Africa, Antarctica. What am I?", "The letter 'O'"),
    ("You'll find me in all of February, August, June but in none of Green, Gray, Violet. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Rhombus, absent from Star, Circle, Pentagon, Oval, Square, Triangle. What am I?", "The letter 'H'"),
    ("I'm present in every letter of Saturn, Uranus, Mercury, Venus, absent from Black. What am I?", "The letter 'U'"),
    ("Spot me in Oceania, Asia, Africa, Antarctica; you won't find me in Lead. What am I?", "The letter 'I'"),
    ("In Antarctica, Asia I'm there; in Cello, Flute, Drum, Harp I disappear. Who am I?", "The letter 'I'"),
    ("I appear in North, East, Center yet in Orange I'm gone. Who am I?", "The letter 'T'"),
    ("Spot me in Mercury; you won't find me in Violet, Indigo, Gray. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Saturday, Sunday, Tuesday, Wednesday, absent from January, June. What am I?", "The letter 'S'"),
    ("I appear in Shark yet in Tuesday, Sunday, Wednesday, Saturday I'm gone. Who am I?", "The letter 'H'"),
    ("I'm present in every letter of Tuesday, Sunday, Thursday, Monday, absent from Wolf. What am I?", "The letter 'Y'"),
    ("I appear in Fox yet in Zebra, Otter I'm gone. Who am I?", "The letter 'X'"),
    ("Spot me in Saturday, Sunday, Monday, Tuesday; you won't find me in Saturn, Venus, Mars, Earth. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Wednesday, Tuesday, absent from Friday, Sunday. What am I?", "The letter 'E'"),
    ("Spot me in Peach; you won't find me in January, November. What am I?", "The letter 'C'"),
    ("Spot me in Carbon, Nitrogen; you won't find me in Silver, Gold. What am I?", "The letter 'N'"),
    ("You'll find me in all of Apple, Papaya but in none of Kiwi. What am I?", "The letter 'A'"),
    ("I appear in Wednesday, Friday, Monday, Tuesday yet in Iron, Lead, Gold I'm gone. Who am I?", "The letter 'Y'"),
    ("I'm present in every letter of Orange, absent from Blue, Black. What am I?", "The letter 'N'"),
    ("I appear in Center yet in Indigo, Orange, Green, Violet I'm gone. Who am I?", "The letter 'C'"),
    ("You'll find me in all of Rabbit but in none of August, March, July. What am I?", "The letter 'B'"),
    ("Spot me in Hexagon; you won't find me in Star, Rectangle, Pentagon, Oval, Octagon, Triangle. What am I?", "The letter 'H'"),
    ("You'll find me in all of Saturn, Venus, Mars but in none of Clarinet, Trumpet. What am I?", "The letter 'S'"),
    ("Spot me in West, Center, North; you won't find me in Hockey, Volleyball. What am I?", "The letter 'T'"),
    ("You'll find me in all of Neptune, Mercury, Venus, Earth but in none of Oval. What am I?", "The letter 'E'"),
    ("I appear in Earth yet in Saturn, Jupiter, Mercury, Mars I'm gone. Who am I?", "The letter 'H'"),
    ("I'm present in every letter of Yellow, Brown, absent from Indigo, Violet, Gray, Pink, Red. What am I?", "The letter 'W'"),
    ("In Tuesday, Sunday, Monday, Saturday I'm there; in East, North, West, South I disappear. Who am I?", "The letter 'Y'"),
    ("Spot me in South, East, West; you won't find me in Center, North. What am I?", "The letter 'S'"),
    ("Spot me in Tennis; you won't find me in West, South. What am I?", "The letter 'I'"),
    ("I'm present in every letter of Center, absent from North, West. What am I?", "The letter 'C'"),
    ("You'll find me in all of East but in none of Flute, Clarinet, Piano. What am I?", "The letter 'S'"),
    ("You'll find me in all of October but in none of August, February, July, January, April. What am I?", "The letter 'O'"),
    ("I'm present in every letter of Guitar, Trumpet, absent from Hydrogen. What am I?", "The letter 'T'"),
    ("Spot me in Sunday, Wednesday, Monday, Friday; you won't find me in America, Europe, Africa. What am I?", "The letter 'Y'"),
    ("I'm present in every letter of Cricket, absent from Soccer, Baseball, Volleyball. What am I?", "The letter 'K'"),
    ("I appear in Thursday yet in Monday, Saturday, Sunday I'm gone. Who am I?", "The letter 'H'"),
    ("I appear in March yet in Indigo I'm gone. Who am I?", "The letter 'M'"),
    ("In Tuesday, Saturday, Friday I'm there; in Africa I disappear. Who am I?", "The letter 'D'"),
    ("In Antarctica, America, Oceania, Africa I'm there; in Earth, Jupiter, Saturn I disappear. Who am I?", "The letter 'C'"),
    ("Spot me in Grape, Papaya; you won't find me in Plum, Lemon. What am I?", "The letter 'A'"),
    ("I'm present in every letter of Venus, Neptune, absent from Jupiter. What am I?", "The letter 'N'"),
    ("You'll find me in all of Violin, Saxophone but in none of Drum. What am I?", "The letter 'O'"),
    ("You'll find me in all of Cobra, Otter but in none of Whale, Panda, Rabbit, Zebra. What am I?", "The letter 'O'"),
    ("I'm present in every letter of West, absent from Orange, Indigo, Blue. What am I?", "The letter 'W'"),
    ("I'm present in every letter of April, absent from July, March, November, December, August, January. What am I?", "The letter 'P'"),
    ("Spot me in Piano, Harp; you won't find me in Sunday, Wednesday. What am I?", "The letter 'P'"),
    ("I'm present in every letter of Center, East, South, West, absent from Africa, Oceania. What am I?", "The letter 'T'"),
    ("In Trumpet, Harp I'm there; in Clarinet I disappear. Who am I?", "The letter 'P'"),
    ("I'm present in every letter of Star, Square, absent from Panda. What am I?", "The letter 'S'"),
    ("In Sunday, Thursday, Saturday I'm there; in East, North I disappear. Who am I?", "The letter 'U'"),
    ("I appear in Europe yet in Oceania, Antarctica I'm gone. Who am I?", "The letter 'P'"),
    ("I appear in Saturn yet in Bear I'm gone. Who am I?", "The letter 'U'"),
    ("I'm present in every letter of Triangle, Rectangle, absent from Friday, Wednesday, Saturday, Thursday. What am I?", "The letter 'L'"),
    ("Spot me in July, February, May; you won't find me in March, October, June. What am I?", "The letter 'Y'"),
    ("Spot me in North; you won't find me in West, South. What am I?", "The letter 'R'"),
    ("I appear in Friday yet in Saturday, Thursday, Sunday, Wednesday I'm gone. Who am I?", "The letter 'F'"),
    ("In Otter, Lion, Cobra I'm there; in Shark I disappear. Who am I?", "The letter 'O'"),
    ("I appear in Panda, Bear yet in Cricket I'm gone. Who am I?", "The letter 'A'"),
    ("I appear in Piano yet in Sulfur, Lead I'm gone. Who am I?", "The letter 'N'"),
    ("Spot me in December, November, January, March; you won't find me in Monday. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Jupiter, Mercury, Uranus, absent from Neptune. What am I?", "The letter 'R'"),
    ("Spot me in September, August; you won't find me in March. What am I?", "The letter 'T'"),
    ("In Black I'm there; in Soccer I disappear. Who am I?", "The letter 'A'"),
    ("In March, April I'm there; in July, August I disappear. Who am I?", "The letter 'R'"),
    ("I appear in Clarinet yet in Neptune, Mercury, Mars, Earth I'm gone. Who am I?", "The letter 'L'"),
    ("I appear in Africa yet in August, July I'm gone. Who am I?", "The letter 'F'"),
    ("In East, South I'm there; in Cherry, Plum, Apple, Peach I disappear. Who am I?", "The letter 'S'"),
    ("Spot me in Jupiter; you won't find me in Venus, Uranus. What am I?", "The letter 'T'"),
    ("In December I'm there; in Cherry, Lime, Peach, Banana I disappear. Who am I?", "The letter 'D'"),
    ("I'm present in every letter of Antarctica, Oceania, Africa, absent from Lemon, Papaya. What am I?", "The letter 'C'"),
    ("I'm present in every letter of Mars, absent from Nitrogen, Oxygen. What am I?", "The letter 'M'"),
    ("I appear in Silver yet in Hydrogen, Gold, Carbon I'm gone. Who am I?", "The letter 'I'"),
    ("Spot me in Lead, Nitrogen, Oxygen; you won't find me in Drum. What am I?", "The letter 'E'"),
    ("You'll find me in all of Moose but in none of Giraffe, Tiger, Donkey, Bear, Whale, Yak. What am I?", "The letter 'M'"),
    ("In Mars I'm there; in Piano I disappear. Who am I?", "The letter 'S'"),
    ("You'll find me in all of Brown, Orange, Yellow but in none of Drum, Guitar, Flute. What am I?", "The letter 'O'"),
    ("I'm present in every letter of Africa, Antarctica, Asia, absent from Square, Octagon. What am I?", "The letter 'I'"),
    ("Spot me in Asia; you won't find me in Harp, Guitar, Trumpet. What am I?", "The letter 'S'"),
    ("Spot me in Flute; you won't find me in Black, Violet, Red. What am I?", "The letter 'U'"),
    ("I appear in Saturday, Sunday yet in September, April, June, July I'm gone. Who am I?", "The letter 'D'"),
    ("You'll find me in all of April, July but in none of August. What am I?", "The letter 'L'"),
    ("Spot me in Hexagon, Rectangle, Square; you won't find me in Octagon. What am I?", "The letter 'E'"),
    ("Spot me in Violin; you won't find me in Guitar, Harp, Drum. What am I?", "The letter 'O'"),
    ("I appear in Oceania yet in America, Europe I'm gone. Who am I?", "The letter 'N'"),
    ("I'm present in every letter of Mercury, absent from May, December. What am I?", "The letter 'U'"),
    ("Spot me in February; you won't find me in March, October. What am I?", "The letter 'F'"),
    ("Spot me in Hexagon; you won't find me in Rectangle, Star, Octagon, Circle, Square. What am I?", "The letter 'H'"),
    ("I'm present in every letter of Sulfur, absent from Tuesday, Sunday. What am I?", "The letter 'F'"),
    ("I'm present in every letter of Wednesday, Thursday, absent from Friday. What am I?", "The letter 'S'"),
    ("I appear in Flute, Guitar yet in Clarinet, Cello I'm gone. Who am I?", "The letter 'U'"),
    ("I appear in Tennis yet in Hockey, Soccer, Baseball, Basketball I'm gone. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Black, Gray, absent from Blue. What am I?", "The letter 'A'"),
    ("I appear in Thursday, Monday yet in West, North I'm gone. Who am I?", "The letter 'Y'"),
    ("I appear in Wednesday yet in Tuesday, Monday, Sunday, Saturday, Friday, Thursday I'm gone. Who am I?", "The letter 'W'"),
    ("You'll find me in all of Volleyball but in none of Kiwi, Grape, Mango. What am I?", "The letter 'L'"),
    ("You'll find me in all of Friday, Thursday, Tuesday, Sunday but in none of Clarinet, Flute. What am I?", "The letter 'D'"),
    ("You'll find me in all of America but in none of Europe, Africa. What am I?", "The letter 'M'"),
    ("You'll find me in all of Cricket, Basketball but in none of Soccer, Football, Golf. What am I?", "The letter 'K'"),
    ("I appear in Golf, Basketball, Football yet in Tuesday, Friday, Saturday I'm gone. Who am I?", "The letter 'L'"),
    ("Spot me in Triangle; you won't find me in Cobra, Donkey, Monkey, Otter. What am I?", "The letter 'G'"),
    ("You'll find me in all of Wednesday, Saturday but in none of North, South, West. What am I?", "The letter 'D'"),
    ("You'll find me in all of Trumpet, Harp, Saxophone but in none of Violin, Clarinet, Cello, Guitar. What am I?", "The letter 'P'"),
    ("You'll find me in all of West but in none of East, North. What am I?", "The letter 'W'"),
    ("You'll find me in all of Shark, Monkey but in none of Flute, Violin, Guitar. What am I?", "The letter 'K'"),
    ("You'll find me in all of Sunday, Saturday, Friday but in none of Rectangle, Octagon, Star, Oval. What am I?", "The letter 'Y'"),
    ("In Whale I'm there; in Pentagon, Triangle, Oval, Rhombus I disappear. Who am I?", "The letter 'W'"),
    ("Spot me in Papaya; you won't find me in Earth. What am I?", "The letter 'Y'"),
    ("I appear in Antarctica, Oceania yet in Hexagon, Rectangle, Square I'm gone. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Basketball, absent from Golf, Football. What am I?", "The letter 'K'"),
    ("In Violet I'm there; in Pink, Brown I disappear. Who am I?", "The letter 'L'"),
    ("In Trumpet, Saxophone I'm there; in Clarinet I disappear. Who am I?", "The letter 'P'"),
    ("I appear in Star, Pentagon, Oval yet in South, West, Center I'm gone. Who am I?", "The letter 'A'"),
    ("In Lime I'm there; in Antarctica I disappear. Who am I?", "The letter 'L'"),
    ("You'll find me in all of Tuesday but in none of Lion, Whale, Wolf, Bear. What am I?", "The letter 'Y'"),
    ("I appear in Violin, Piano yet in Pentagon, Star, Square, Oval I'm gone. Who am I?", "The letter 'I'"),
    ("In Saturn I'm there; in Cricket, Golf, Baseball I disappear. Who am I?", "The letter 'U'"),
    ("You'll find me in all of Wednesday, Saturday, Thursday, Sunday but in none of Flute. What am I?", "The letter 'Y'"),
    ("I appear in Pink yet in Cherry, Grape I'm gone. Who am I?", "The letter 'N'"),
    ("I appear in Rugby yet in Center, North, East I'm gone. Who am I?", "The letter 'B'"),
    ("You'll find me in all of Saxophone, Trumpet, Harp but in none of East, South. What am I?", "The letter 'P'"),
    ("In Apple, Cherry, Peach, Lemon I'm there; in Thursday I disappear. Who am I?", "The letter 'E'"),
    ("I'm present in every letter of Flute, Violin, Cello, absent from Trumpet, Guitar. What am I?", "The letter 'L'"),
    ("You'll find me in all of Fox but in none of West, Center. What am I?", "The letter 'F'"),
    ("I appear in Panda yet in Zebra, Wolf I'm gone. Who am I?", "The letter 'N'"),
    ("You'll find me in all of Baseball, Football but in none of Golf, Hockey, Cricket. What am I?", "The letter 'A'"),
    ("I'm present in every letter of Cobra, absent from Sunday, Tuesday. What am I?", "The letter 'R'"),
    ("In Blue I'm there; in Violet, Yellow, Red I disappear. Who am I?", "The letter 'U'"),
    ("You'll find me in all of Banana but in none of Orange, Mango. What am I?", "The letter 'B'"),
    ("In October I'm there; in June, February, November I disappear. Who am I?", "The letter 'T'"),
    ("In Asia I'm there; in Antarctica, Africa I disappear. Who am I?", "The letter 'S'"),
    ("You'll find me in all of Neptune, Earth but in none of Mars. What am I?", "The letter 'T'"),
    ("I'm present in every letter of Fox, absent from Gold. What am I?", "The letter 'X'"),
    ("You'll find me in all of East but in none of Sunday. What am I?", "The letter 'T'"),
    ("You'll find me in all of Silver, Lead, Sulfur but in none of Tin. What am I?", "The letter 'L'"),
    ("I'm present in every letter of Tuesday, absent from Sunday, Monday. What am I?", "The letter 'T'"),
    ("I appear in Wednesday, Monday yet in January, September I'm gone. Who am I?", "The letter 'D'"),
    ("I'm present in every letter of Star, absent from Pentagon, Rectangle. What am I?", "The letter 'S'"),
    ("Spot me in Harp; you won't find me in Flute, Trumpet, Violin. What am I?", "The letter 'H'"),
    ("I appear in Indigo yet in Gray, Orange, Violet I'm gone. Who am I?", "The letter 'D'"),
    ("I appear in White, Yellow, Green, Violet yet in Black I'm gone. Who am I?", "The letter 'E'"),
    ("I appear in April yet in November, February, October, September, August, June I'm gone. Who am I?", "The letter 'I'"),
    ("I appear in Oxygen yet in Silver, Sulfur I'm gone. Who am I?", "The letter 'Y'"),
    ("I appear in Uranus, Mercury, Mars, Saturn yet in Volleyball I'm gone. Who am I?", "The letter 'R'"),
    ("You'll find me in all of West, Center but in none of North. What am I?", "The letter 'E'"),
    ("I'm present in every letter of Indigo, absent from Gray, Violet. What am I?", "The letter 'D'"),
    ("I appear in Volleyball yet in Baseball, Hockey I'm gone. Who am I?", "The letter 'V'"),
    ("I appear in Pentagon, Hexagon, Oval, Rhombus yet in Triangle I'm gone. Who am I?", "The letter 'O'"),
    ("You'll find me in all of Red but in none of Blue, Gray, Pink. What am I?", "The letter 'D'"),
    ("I appear in Oceania yet in Saturday I'm gone. Who am I?", "The letter 'O'"),
    ("I'm present in every letter of Friday, Monday, Sunday, absent from Center, East, North. What am I?", "The letter 'D'"),
    ("Spot me in East, West; you won't find me in Center, North. What am I?", "The letter 'S'"),
    ("I appear in South yet in North, Center, West, East I'm gone. Who am I?", "The letter 'U'"),
    ("I appear in Soccer yet in Monday I'm gone. Who am I?", "The letter 'S'"),
    ("Spot me in Mercury, Venus, Uranus, Jupiter; you won't find me in Star. What am I?", "The letter 'U'"),
    ("In Carbon, Copper I'm there; in Oxygen I disappear. Who am I?", "The letter 'R'"),
    ("I appear in Asia, Antarctica yet in Gold I'm gone. Who am I?", "The letter 'A'"),
    ("I appear in Orange, Pear, Apple yet in Iron, Tin, Silver, Nitrogen I'm gone. Who am I?", "The letter 'A'"),
    ("Spot me in Pentagon; you won't find me in Venus, Saturn, Jupiter, Earth. What am I?", "The letter 'O'"),
    ("I'm present in every letter of Asia, America, Oceania, absent from Yak. What am I?", "The letter 'I'"),
    ("I'm present in every letter of Earth, absent from Neptune, Jupiter. What am I?", "The letter 'A'"),
    ("In Rabbit I'm there; in Wednesday, Monday, Sunday I disappear. Who am I?", "The letter 'B'"),
    ("Spot me in Iron; you won't find me in Sulfur, Hydrogen. What am I?", "The letter 'I'"),
    ("I appear in Saturn yet in Mercury, Neptune, Jupiter, Earth I'm gone. Who am I?", "The letter 'S'"),
    ("I'm present in every letter of Giraffe, Moose, absent from Rabbit. What am I?", "The letter 'E'"),
    ("You'll find me in all of Mars but in none of Tennis, Golf, Cricket, Basketball. What am I?", "The letter 'M'"),
    ("You'll find me in all of Rabbit but in none of Black, Yellow, Brown, Pink. What am I?", "The letter 'T'"),
    ("Spot me in Yellow, Violet; you won't find me in Plum, Peach, Lime, Cherry. What am I?", "The letter 'O'"),
    ("I appear in Tuesday yet in South I'm gone. Who am I?", "The letter 'E'"),
    ("I'm present in every letter of Red, absent from Copper, Carbon. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Apple, absent from Yellow. What am I?", "The letter 'A'"),
    ("I appear in Baseball yet in June, November, March, October I'm gone. Who am I?", "The letter 'L'"),
    ("You'll find me in all of Wednesday but in none of Golf. What am I?", "The letter 'N'"),
    ("I'm present in every letter of Earth, absent from Center. What am I?", "The letter 'H'"),
    ("I'm present in every letter of Earth, Saturn, absent from Helium, Gold, Tin, Silver. What am I?", "The letter 'A'"),
    ("In Earth, Mars, Uranus I'm there; in Venus I disappear. Who am I?", "The letter 'A'"),
    ("I appear in West yet in Europe, Asia, Africa I'm gone. Who am I?", "The letter 'W'"),
    ("Spot me in Mars, Saturn, Earth; you won't find me in Mango, Lime. What am I?", "The letter 'R'"),
    ("In North I'm there; in Mars, Uranus, Saturn I disappear. Who am I?", "The letter 'O'"),
    ("I appear in September, August yet in July, December, April I'm gone. Who am I?", "The letter 'T'"),
    ("I'm present in every letter of Indigo, absent from Gray, Orange. What am I?", "The letter 'D'"),
    ("I appear in Antarctica yet in Saturday, Tuesday, Monday, Thursday I'm gone. Who am I?", "The letter 'C'"),
    ("You'll find me in all of Lime but in none of Apple, Orange. What am I?", "The letter 'M'"),
    ("I appear in April yet in March, January, June I'm gone. Who am I?", "The letter 'L'"),
    ("I'm present in every letter of Asia, Oceania, absent from Green, Pink, Violet. What am I?", "The letter 'A'"),
    ("I appear in Mercury, Earth yet in Pentagon, Oval, Octagon I'm gone. Who am I?", "The letter 'R'"),
    ("You'll find me in all of Hockey, Baseball but in none of Gold. What am I?", "The letter 'E'"),
    ("I'm present in every letter of Oceania, absent from Uranus, Venus. What am I?", "The letter 'C'"),
    ("You'll find me in all of Papaya, Apple but in none of Saturn, Venus. What am I?", "The letter 'P'"),
    ("You'll find me in all of Hexagon, Octagon but in none of Circle, Square, Star, Oval, Rhombus. What am I?", "The letter 'G'"),
    ("In South I'm there; in North, Center I disappear. Who am I?", "The letter 'S'"),
    ("Spot me in Triangle, Oval, Rectangle; you won't find me in Hexagon. What am I?", "The letter 'L'"),
    ("I appear in Friday, Monday, Wednesday yet in Center, South I'm gone. Who am I?", "The letter 'A'"),
    ("In June, January I'm there; in October I disappear. Who am I?", "The letter 'J'"),
    ("I appear in Pear yet in West I'm gone. Who am I?", "The letter 'R'"),
    ("I appear in Lead, Sulfur, Silver, Gold yet in Hydrogen I'm gone. Who am I?", "The letter 'L'"),
    ("Spot me in Violin, Saxophone; you won't find me in Harp, Trumpet. What am I?", "The letter 'O'"),
    ("Spot me in Monday, Sunday, Thursday; you won't find me in Red, Violet, Brown. What am I?", "The letter 'Y'"),
    ("Spot me in Monday; you won't find me in Mercury, Mars, Uranus. What am I?", "The letter 'O'"),
    ("Spot me in Violin; you won't find me in Guitar, Cello, Harp, Piano, Saxophone. What am I?", "The letter 'V'"),
    ("In October, September I'm there; in August I disappear. Who am I?", "The letter 'B'"),
    ("I'm present in every letter of Antarctica, absent from Oceania, America, Africa, Asia, Europe. What am I?", "The letter 'T'"),
    ("I appear in Baseball, Volleyball yet in Golf, Cricket, Soccer, Rugby, Tennis I'm gone. Who am I?", "The letter 'A'"),
    ("I appear in Lion yet in Orange, Apple I'm gone. Who am I?", "The letter 'I'"),
    ("Spot me in Panda, Whale, Cobra; you won't find me in Wolf, Donkey. What am I?", "The letter 'A'"),
    ("I'm present in every letter of Monday, absent from Saturday, Thursday, Friday, Tuesday, Wednesday, Sunday. What am I?", "The letter 'O'"),
    ("I appear in Europe, Oceania yet in Antarctica, Asia I'm gone. Who am I?", "The letter 'O'"),
    ("Spot me in Shark, Cobra; you won't find me in Panda. What am I?", "The letter 'R'"),
    ("Spot me in Brown; you won't find me in White, Green, Gray, Indigo, Pink. What am I?", "The letter 'B'"),
    ("In Star, Hexagon I'm there; in Brown, Blue, Violet, Red I disappear. Who am I?", "The letter 'A'"),
    ("Spot me in Volleyball; you won't find me in Cricket, Hockey, Rugby. What am I?", "The letter 'L'"),
    ("In North, South I'm there; in Cherry, Grape I disappear. Who am I?", "The letter 'O'"),
    ("I'm present in every letter of Friday, Wednesday, Tuesday, Saturday, absent from Donkey. What am I?", "The letter 'A'"),
    ("I appear in Antarctica, Asia yet in Yak, Wolf, Bear I'm gone. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of December, absent from Trumpet, Cello. What am I?", "The letter 'B'"),
    ("Spot me in Papaya; you won't find me in Carbon, Iron. What am I?", "The letter 'P'"),
    ("I appear in Gold, Lead yet in Nitrogen I'm gone. Who am I?", "The letter 'L'"),
    ("You'll find me in all of Saxophone, Clarinet but in none of Violin. What am I?", "The letter 'A'"),
    ("I'm present in every letter of February, absent from November, May, July. What am I?", "The letter 'F'"),
    ("Spot me in Golf; you won't find me in Tennis, Baseball, Soccer. What am I?", "The letter 'F'"),
    ("You'll find me in all of America but in none of Africa, Oceania, Asia, Europe. What am I?", "The letter 'M'"),
    ("Spot me in Wednesday; you won't find me in Thursday, Tuesday. What am I?", "The letter 'W'"),
    ("In Banana I'm there; in Lime, Plum, Peach, Lemon, Orange I disappear. Who am I?", "The letter 'B'"),
    ("Spot me in Center, East; you won't find me in North. What am I?", "The letter 'E'"),
    ("I appear in Monday yet in Harp, Flute, Guitar I'm gone. Who am I?", "The letter 'N'"),
    ("You'll find me in all of Saturn, Mars but in none of Mercury. What am I?", "The letter 'A'"),
    ("In Thursday, Wednesday, Sunday, Tuesday I'm there; in Tennis I disappear. Who am I?", "The letter 'Y'"),
    ("You'll find me in all of Circle but in none of Indigo, Gray, Black. What am I?", "The letter 'E'"),
    ("You'll find me in all of Golf, Volleyball, Baseball but in none of Soccer. What am I?", "The letter 'L'"),
    ("In September I'm there; in January, March, February I disappear. Who am I?", "The letter 'T'"),
    ("I appear in October, December yet in November, August, April, May I'm gone. Who am I?", "The letter 'C'"),
    ("In South I'm there; in Center, East I disappear. Who am I?", "The letter 'H'"),
    ("I'm present in every letter of Indigo, absent from Mercury. What am I?", "The letter 'I'"),
    ("You'll find me in all of Antarctica but in none of Asia, Africa. What am I?", "The letter 'N'"),
    ("I appear in Monkey yet in Baseball, Rugby I'm gone. Who am I?", "The letter 'O'"),
    ("You'll find me in all of Friday, Monday but in none of Tennis, Hockey, Basketball. What am I?", "The letter 'D'"),
    ("In Venus I'm there; in Apple I disappear. Who am I?", "The letter 'U'"),
    ("You'll find me in all of Copper but in none of Nitrogen, Tin. What am I?", "The letter 'C'"),
    ("Spot me in Basketball, Football, Baseball, Golf; you won't find me in Hockey, Soccer. What am I?", "The letter 'L'"),
    ("In Carbon I'm there; in Violin, Piano, Trumpet I disappear. Who am I?", "The letter 'B'"),
    ("In Monkey I'm there; in Earth I disappear. Who am I?", "The letter 'Y'"),
    ("You'll find me in all of Venus, Neptune, Mercury but in none of Center, North. What am I?", "The letter 'U'"),
    ("You'll find me in all of Center, North, South, East but in none of Kiwi, Peach, Lime. What am I?", "The letter 'T'"),
    ("In Cricket I'm there; in Baseball, Soccer, Basketball, Volleyball I disappear. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Africa, absent from Green. What am I?", "The letter 'C'"),
    ("You'll find me in all of Uranus but in none of Plum, Lime, Banana. What am I?", "The letter 'S'"),
    ("I'm present in every letter of East, absent from Center, North. What am I?", "The letter 'S'"),
    ("I appear in Black, Blue, Brown yet in Africa, Europe I'm gone. Who am I?", "The letter 'B'"),
    ("I'm present in every letter of Helium, absent from Oxygen, Iron, Sulfur. What am I?", "The letter 'M'"),
    ("I appear in Cobra yet in Hockey, Rugby I'm gone. Who am I?", "The letter 'A'"),
    ("You'll find me in all of Africa, Oceania, America but in none of Europe. What am I?", "The letter 'I'"),
    ("You'll find me in all of Plum but in none of Nitrogen. What am I?", "The letter 'U'"),
    ("Spot me in February; you won't find me in July, November, April, August, March. What am I?", "The letter 'F'"),
    ("Spot me in Basketball, Volleyball; you won't find me in Yellow. What am I?", "The letter 'A'"),
    ("In Cello I'm there; in West I disappear. Who am I?", "The letter 'L'"),
    ("Spot me in Venus; you won't find me in January, August, April. What am I?", "The letter 'E'"),
    ("I appear in August yet in Monkey I'm gone. Who am I?", "The letter 'G'"),
    ("Spot me in Saxophone; you won't find me in Nitrogen, Oxygen, Iron. What am I?", "The letter 'H'"),
    ("I'm present in every letter of Zebra, absent from Flute. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Asia, absent from Piano, Harp. What am I?", "The letter 'S'"),
    ("I appear in Lemon yet in Cobra, Rabbit, Shark I'm gone. Who am I?", "The letter 'M'"),
    ("You'll find me in all of Basketball but in none of Saturday, Friday, Sunday, Thursday. What am I?", "The letter 'E'"),
    ("I appear in Soccer, Football, Hockey yet in Wednesday I'm gone. Who am I?", "The letter 'O'"),
    ("In Oceania, Asia I'm there; in Octagon, Rectangle I disappear. Who am I?", "The letter 'I'"),
    ("You'll find me in all of North but in none of East, Center. What am I?", "The letter 'H'"),
    ("You'll find me in all of Banana but in none of Violet, Red. What am I?", "The letter 'A'"),
    ("I'm present in every letter of Mango, absent from Mars. What am I?", "The letter 'N'"),
    ("You'll find me in all of Football, Volleyball but in none of Basketball. What am I?", "The letter 'O'"),
    ("I'm present in every letter of Black, absent from Yellow, Orange, Pink, White, Red, Indigo. What am I?", "The letter 'B'"),
    ("You'll find me in all of Volleyball but in none of Guitar, Piano, Violin. What am I?", "The letter 'Y'"),
    ("I appear in North, South, Center yet in Carbon I'm gone. Who am I?", "The letter 'T'"),
    ("You'll find me in all of Volleyball but in none of Football, Baseball, Golf. What am I?", "The letter 'V'"),
    ("In South I'm there; in North, West, Center, East I disappear. Who am I?", "The letter 'U'"),
    ("Spot me in Piano, Saxophone; you won't find me in Clarinet, Guitar, Harp. What am I?", "The letter 'O'"),
    ("You'll find me in all of Indigo, White but in none of Red. What am I?", "The letter 'I'"),
    ("I appear in Saxophone, Trumpet yet in Piano I'm gone. Who am I?", "The letter 'E'"),
    ("Spot me in Orange; you won't find me in Plum, Cherry, Grape. What am I?", "The letter 'N'"),
    ("I appear in Carbon yet in Tin, Iron, Hydrogen I'm gone. Who am I?", "The letter 'B'"),
    ("In Trumpet, Harp, Piano I'm there; in Cello, Flute, Guitar I disappear. Who am I?", "The letter 'P'"),
    ("I'm present in every letter of February, November, absent from April. What am I?", "The letter 'E'"),
    ("In West, East I'm there; in South I disappear. Who am I?", "The letter 'E'"),
    ("I appear in Saturday yet in North, Center I'm gone. Who am I?", "The letter 'U'"),
    ("I appear in Orange yet in Kiwi, Mango I'm gone. Who am I?", "The letter 'R'"),
    ("In Antarctica, Africa I'm there; in Tiger, Moose, Donkey, Monkey I disappear. Who am I?", "The letter 'C'"),
    ("I'm present in every letter of Friday, Monday, Tuesday, absent from Peach, Banana, Kiwi. What am I?", "The letter 'D'"),
    ("In Tuesday, Saturday I'm there; in Hockey, Soccer, Rugby, Tennis I disappear. Who am I?", "The letter 'D'"),
    ("Spot me in Oval; you won't find me in Rectangle, Square, Hexagon, Pentagon, Star. What am I?", "The letter 'V'"),
    ("In Europe I'm there; in Africa, Antarctica I disappear. Who am I?", "The letter 'E'"),
    ("I'm present in every letter of May, absent from Hydrogen, Lead, Iron, Carbon. What am I?", "The letter 'M'"),
    ("I'm present in every letter of Lime, absent from Papaya, Lemon, Peach, Apple, Pear, Mango. What am I?", "The letter 'I'"),
    ("Spot me in East; you won't find me in Hockey. What am I?", "The letter 'A'"),
    ("Spot me in Earth; you won't find me in Hockey, Golf. What am I?", "The letter 'A'"),
    ("I appear in Whale yet in Wolf, Yak, Otter I'm gone. Who am I?", "The letter 'H'"),
    ("I'm present in every letter of South, absent from North, East, Center, West. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Triangle, Star, absent from Pentagon. What am I?", "The letter 'R'"),
    ("In Friday, Saturday, Thursday I'm there; in Antarctica, Europe, America I disappear. Who am I?", "The letter 'D'"),
    ("You'll find me in all of August, September but in none of November, July, May, June, January. What am I?", "The letter 'S'"),
    ("Spot me in Uranus, Neptune; you won't find me in White. What am I?", "The letter 'U'"),
    ("In Clarinet I'm there; in Harp, Trumpet, Drum, Violin, Flute I disappear. Who am I?", "The letter 'C'"),
    ("I'm present in every letter of Yellow, absent from Pear. What am I?", "The letter 'O'"),
    ("I'm present in every letter of May, August, March, absent from September. What am I?", "The letter 'A'"),
    ("In Thursday, Tuesday, Wednesday I'm there; in Circle, Oval, Star, Square I disappear. Who am I?", "The letter 'D'"),
    ("Spot me in Black; you won't find me in Brown, Pink, Indigo. What am I?", "The letter 'C'"),
    ("I appear in Yak, Monkey yet in Shark, Whale, Zebra, Bear I'm gone. Who am I?", "The letter 'Y'"),
    ("In Otter, Zebra I'm there; in Saturday I disappear. Who am I?", "The letter 'E'"),
    ("I appear in Lion yet in Whale, Donkey I'm gone. Who am I?", "The letter 'I'"),
    ("I appear in West yet in North, South, Center I'm gone. Who am I?", "The letter 'W'"),
    ("You'll find me in all of West but in none of Monday. What am I?", "The letter 'W'"),
    ("In Tuesday, Wednesday I'm there; in Yellow, Green, Brown, Orange I disappear. Who am I?", "The letter 'D'"),
    ("Spot me in Cricket, Basketball, Baseball; you won't find me in Football. What am I?", "The letter 'E'"),
    ("I appear in Square, Rhombus, Triangle yet in Hexagon I'm gone. Who am I?", "The letter 'R'"),
    ("You'll find me in all of Oval, Triangle, Hexagon but in none of Circle. What am I?", "The letter 'A'"),
    ("I appear in White yet in Helium, Iron I'm gone. Who am I?", "The letter 'W'"),
    ("I appear in South yet in Sunday, Saturday I'm gone. Who am I?", "The letter 'H'"),
    ("In Star, Pentagon I'm there; in November I disappear. Who am I?", "The letter 'T'"),
    ("I appear in Kiwi yet in Pentagon, Square I'm gone. Who am I?", "The letter 'I'"),
    ("I appear in Saturn, Uranus, Mercury, Neptune yet in America, Antarctica, Oceania I'm gone. Who am I?", "The letter 'U'"),
    ("In Europe I'm there; in Grape, Kiwi, Orange, Lemon I disappear. Who am I?", "The letter 'U'"),
    ("I'm present in every letter of Earth, absent from Africa, Europe, America. What am I?", "The letter 'H'"),
    ("In Venus I'm there; in Oval I disappear. Who am I?", "The letter 'S'"),
    ("I'm present in every letter of Basketball, Cricket, Tennis, absent from Golf. What am I?", "The letter 'E'"),
    ("Spot me in Center, South, East; you won't find me in Gray, Red, Indigo, Black. What am I?", "The letter 'T'"),
    ("In Center, West, North, South I'm there; in June, March, November, December I disappear. Who am I?", "The letter 'T'"),
    ("Spot me in Nitrogen, Oxygen, Carbon; you won't find me in Earth, Neptune, Saturn. What am I?", "The letter 'O'"),
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
    batch_duplicates = check_duplicates_in_batch(riddles_batch3)
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

    for i, (question, answer) in enumerate(riddles_batch3):
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
    print(f"- Total riddles in batch: {len(riddles_batch3)}")
    print(f"- Added to database: {added_count}")
    print(f"- Skipped (duplicates): {skipped_duplicates}")
    print(f"- Batch duplicates found: {len(batch_duplicates)}")

if __name__ == "__main__":
    add_riddles_to_db()