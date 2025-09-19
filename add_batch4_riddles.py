#!/usr/bin/env python3
import sqlite3
import re
import string

# New riddles batch 4
riddles_batch4 = [
    ("I appear in Hydrogen yet in Piano, Cello, Clarinet I'm gone. Who am I?", "The letter 'Y'"),
    ("In January I'm there; in Piano, Clarinet, Cello I disappear. Who am I?", "The letter 'U'"),
    ("In South, North, East, Center I'm there; in Donkey, Panda, Lion, Yak I disappear. Who am I?", "The letter 'T'"),
    ("In November, June I'm there; in April I disappear. Who am I?", "The letter 'N'"),
    ("You'll find me in all of Octagon but in none of Hydrogen. What am I?", "The letter 'A'"),
    ("Spot me in Rugby; you won't find me in Trumpet. What am I?", "The letter 'B'"),
    ("You'll find me in all of Venus but in none of Rectangle, Triangle. What am I?", "The letter 'U'"),
    ("In Helium, Silver, Lead I'm there; in Thursday, Sunday, Monday I disappear. Who am I?", "The letter 'E'"),
    ("In Center I'm there; in West, East, North I disappear. Who am I?", "The letter 'C'"),
    ("I'm present in every letter of Iron, Copper, Hydrogen, absent from Helium. What am I?", "The letter 'O'"),
    ("Spot me in Thursday, Friday; you won't find me in Carbon, Copper, Silver. What am I?", "The letter 'Y'"),
    ("I appear in West yet in Rectangle, Oval I'm gone. Who am I?", "The letter 'W'"),
    ("In Asia I'm there; in Wednesday, Monday, Tuesday I disappear. Who am I?", "The letter 'I'"),
    ("Spot me in North, East, Center, South; you won't find me in Volleyball, Rugby. What am I?", "The letter 'T'"),
    ("I'm present in every letter of Rectangle, absent from Lion, Eagle. What am I?", "The letter 'T'"),
    ("I appear in Harp yet in Guitar, Flute I'm gone. Who am I?", "The letter 'H'"),
    ("In Tiger I'm there; in Whale, Yak I disappear. Who am I?", "The letter 'T'"),
    ("In Flute I'm there; in Papaya, Kiwi, Plum I disappear. Who am I?", "The letter 'T'"),
    ("I'm present in every letter of Helium, Sulfur, absent from Earth, Mercury, Neptune. What am I?", "The letter 'L'"),
    ("I'm present in every letter of Center, North, absent from East, South, West. What am I?", "The letter 'R'"),
    ("Spot me in Mercury; you won't find me in South, North, East. What am I?", "The letter 'C'"),
    ("In Square, Octagon, Triangle, Star I'm there; in Nitrogen, Copper I disappear. Who am I?", "The letter 'A'"),
    ("You'll find me in all of Tennis but in none of Football, Rugby, Golf, Basketball. What am I?", "The letter 'I'"),
    ("Spot me in Basketball; you won't find me in Helium. What am I?", "The letter 'A'"),
    ("Spot me in Blue; you won't find me in Yellow, Brown, Pink. What am I?", "The letter 'U'"),
    ("In Grape I'm there; in Lemon, Peach, Banana I disappear. Who am I?", "The letter 'R'"),
    ("In North, Center I'm there; in East, South I disappear. Who am I?", "The letter 'N'"),
    ("I appear in West yet in South, East I'm gone. Who am I?", "The letter 'W'"),
    ("You'll find me in all of Pear but in none of Piano, Flute. What am I?", "The letter 'R'"),
    ("I appear in Pentagon, Star yet in America, Africa I'm gone. Who am I?", "The letter 'T'"),
    ("I appear in Thursday, Sunday, Monday, Friday yet in Cello, Trumpet I'm gone. Who am I?", "The letter 'Y'"),
    ("You'll find me in all of July but in none of Friday, Thursday, Sunday. What am I?", "The letter 'J'"),
    ("In South, West, North I'm there; in Asia, Oceania, America I disappear. Who am I?", "The letter 'T'"),
    ("I'm present in every letter of Lion, absent from Panda, Fox, Monkey, Yak, Donkey, Giraffe. What am I?", "The letter 'L'"),
    ("You'll find me in all of Pear, Apple but in none of Volleyball, Football, Soccer. What am I?", "The letter 'P'"),
    ("In Monday I'm there; in Thursday, Friday, Tuesday I disappear. Who am I?", "The letter 'O'"),
    ("In Wednesday, Monday, Thursday I'm there; in October, June, November, March I disappear. Who am I?", "The letter 'Y'"),
    ("I appear in West, Center yet in Monday, Wednesday I'm gone. Who am I?", "The letter 'T'"),
    ("In Volleyball, Baseball I'm there; in Hockey, Soccer, Rugby I disappear. Who am I?", "The letter 'A'"),
    ("Spot me in Saturn, Jupiter, Mercury, Neptune; you won't find me in Triangle, Star, Octagon. What am I?", "The letter 'U'"),
    ("In November, December I'm there; in February, April, June I disappear. Who am I?", "The letter 'M'"),
    ("In April, November I'm there; in May I disappear. Who am I?", "The letter 'R'"),
    ("I appear in Sunday, Tuesday, Friday, Monday yet in November, February I'm gone. Who am I?", "The letter 'D'"),
    ("You'll find me in all of Clarinet but in none of Trumpet, Guitar. What am I?", "The letter 'C'"),
    ("Spot me in March; you won't find me in Giraffe, Yak. What am I?", "The letter 'H'"),
    ("In Rhombus I'm there; in Pentagon, Circle I disappear. Who am I?", "The letter 'M'"),
    ("Spot me in Triangle; you won't find me in Carbon, Sulfur, Silver. What am I?", "The letter 'T'"),
    ("You'll find me in all of Mercury, Neptune, Earth but in none of Saturn. What am I?", "The letter 'E'"),
    ("You'll find me in all of Cricket but in none of Football, Tennis, Basketball. What am I?", "The letter 'C'"),
    ("I appear in Black yet in Carbon, Nitrogen, Iron I'm gone. Who am I?", "The letter 'L'"),
    ("I appear in Mars yet in Wednesday, Monday I'm gone. Who am I?", "The letter 'R'"),
    ("You'll find me in all of Kiwi but in none of Banana, Grape, Mango, Peach. What am I?", "The letter 'I'"),
    ("I'm present in every letter of Antarctica, Europe, Africa, America, absent from Golf, Tennis. What am I?", "The letter 'R'"),
    ("I appear in Rectangle yet in Mercury, Venus I'm gone. Who am I?", "The letter 'G'"),
    ("Spot me in Asia; you won't find me in America, Oceania, Europe, Antarctica. What am I?", "The letter 'S'"),
    ("I'm present in every letter of Sulfur, absent from Lead, Hydrogen. What am I?", "The letter 'F'"),
    ("I appear in Saturday, Monday, Thursday yet in Square, Rectangle, Circle, Pentagon I'm gone. Who am I?", "The letter 'Y'"),
    ("In Africa I'm there; in Asia, America, Oceania I disappear. Who am I?", "The letter 'F'"),
    ("I'm present in every letter of South, absent from Center, East, North, West. What am I?", "The letter 'U'"),
    ("I appear in Saturday, Friday yet in Mercury, Saturn I'm gone. Who am I?", "The letter 'D'"),
    ("I appear in Neptune, Jupiter yet in Europe, Oceania, America I'm gone. Who am I?", "The letter 'T'"),
    ("In Tuesday, Sunday, Saturday I'm there; in Wednesday, Monday, Friday I disappear. Who am I?", "The letter 'U'"),
    ("In Antarctica I'm there; in January, November, April I disappear. Who am I?", "The letter 'T'"),
    ("I'm present in every letter of Silver, Nitrogen, absent from Tin, Helium. What am I?", "The letter 'R'"),
    ("In Harp I'm there; in Clarinet, Flute, Violin, Drum I disappear. Who am I?", "The letter 'H'"),
    ("I appear in Sulfur yet in Guitar I'm gone. Who am I?", "The letter 'F'"),
    ("I'm present in every letter of Mango, absent from Papaya, Apple, Cherry, Lemon, Lime. What am I?", "The letter 'G'"),
    ("You'll find me in all of Uranus, Mercury, Jupiter, Venus but in none of Kiwi. What am I?", "The letter 'U'"),
    ("You'll find me in all of White but in none of Flute. What am I?", "The letter 'W'"),
    ("I appear in Flute yet in Saxophone, Guitar, Drum, Piano, Cello, Trumpet I'm gone. Who am I?", "The letter 'F'"),
    ("In Venus, Jupiter I'm there; in Violet I disappear. Who am I?", "The letter 'U'"),
    ("I appear in Mercury yet in Venus, Uranus I'm gone. Who am I?", "The letter 'Y'"),
    ("Spot me in Center, North, East; you won't find me in Kiwi, Grape, Lime. What am I?", "The letter 'T'"),
    ("Spot me in Baseball; you won't find me in Violet, Black, White, Indigo. What am I?", "The letter 'S'"),
    ("You'll find me in all of Rugby but in none of Cricket, Hockey, Basketball, Tennis, Golf, Baseball. What am I?", "The letter 'U'"),
    ("You'll find me in all of Oceania but in none of Asia, Africa. What am I?", "The letter 'N'"),
    ("You'll find me in all of Mercury, Saturn, Uranus, Neptune but in none of Mars. What am I?", "The letter 'U'"),
    ("In West I'm there; in Center, South I disappear. Who am I?", "The letter 'W'"),
    ("In Hockey, Cricket I'm there; in Baseball, Volleyball, Soccer I disappear. Who am I?", "The letter 'K'"),
    ("Spot me in Africa; you won't find me in Wednesday, Thursday, Sunday. What am I?", "The letter 'C'"),
    ("You'll find me in all of Sunday, Thursday but in none of Golf, Volleyball, Football. What am I?", "The letter 'S'"),
    ("In Volleyball I'm there; in August, January, February, May I disappear. Who am I?", "The letter 'O'"),
    ("I appear in Piano, Clarinet yet in Saxophone I'm gone. Who am I?", "The letter 'I'"),
    ("In Center I'm there; in East, West, North, South I disappear. Who am I?", "The letter 'C'"),
    ("In Earth, Saturn I'm there; in Mars, Uranus I disappear. Who am I?", "The letter 'T'"),
    ("You'll find me in all of America, Asia, Antarctica but in none of Basketball, Volleyball, Hockey. What am I?", "The letter 'I'"),
    ("Spot me in Monday, Saturday; you won't find me in Lemon, Lime, Apple. What am I?", "The letter 'Y'"),
    ("I'm present in every letter of Thursday, Saturday, absent from Monday, Sunday, Wednesday, Tuesday. What am I?", "The letter 'R'"),
    ("In Lead I'm there; in Star, Triangle, Pentagon, Oval I disappear. Who am I?", "The letter 'D'"),
    ("You'll find me in all of Clarinet but in none of Sulfur, Helium, Carbon. What am I?", "The letter 'T'"),
    ("I appear in Baseball yet in Soccer, Cricket, Tennis, Golf I'm gone. Who am I?", "The letter 'A'"),
    ("I'm present in every letter of September, absent from May, March, November. What am I?", "The letter 'P'"),
    ("You'll find me in all of Earth, Uranus but in none of May. What am I?", "The letter 'R'"),
    ("In Oxygen I'm there; in Pink I disappear. Who am I?", "The letter 'E'"),
    ("I'm present in every letter of Hockey, Rugby, absent from October. What am I?", "The letter 'Y'"),
    ("I'm present in every letter of Lead, absent from Grape, Lime, Banana. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Tennis, Cricket, Hockey, absent from Football, Golf. What am I?", "The letter 'E'"),
    ("I appear in Saxophone, Violin, Cello yet in July, June, March I'm gone. Who am I?", "The letter 'O'"),
    ("I'm present in every letter of Square, absent from Friday. What am I?", "The letter 'E'"),
    ("I appear in Tuesday, Thursday yet in Rectangle, Rhombus, Triangle, Oval I'm gone. Who am I?", "The letter 'D'"),
    ("I appear in November, May yet in April, July I'm gone. Who am I?", "The letter 'M'"),
    ("In Basketball I'm there; in Soccer, Tennis, Golf, Rugby I disappear. Who am I?", "The letter 'A'"),
    ("I'm present in every letter of August, absent from September, November, February, April, June. What am I?", "The letter 'G'"),
    ("I appear in Mercury yet in Earth, Jupiter, Saturn I'm gone. Who am I?", "The letter 'C'"),
    ("I appear in Gray yet in Green, Black, Indigo I'm gone. Who am I?", "The letter 'Y'"),
    ("I'm present in every letter of Friday, absent from Sunday, Tuesday. What am I?", "The letter 'R'"),
    ("In Soccer I'm there; in America, Europe, Africa I disappear. Who am I?", "The letter 'S'"),
    ("I'm present in every letter of Copper, absent from Helium, Lead, Sulfur, Iron, Gold. What am I?", "The letter 'C'"),
    ("In Star I'm there; in White, Indigo, Yellow I disappear. Who am I?", "The letter 'R'"),
    ("You'll find me in all of Center, South but in none of Peach, Lime, Kiwi. What am I?", "The letter 'T'"),
    ("I appear in Lion, Rabbit, Tiger yet in Soccer I'm gone. Who am I?", "The letter 'I'"),
    ("In March I'm there; in October, September, February I disappear. Who am I?", "The letter 'H'"),
    ("Spot me in Oval, Octagon; you won't find me in Europe. What am I?", "The letter 'A'"),
    ("I appear in Oxygen, Silver yet in April I'm gone. Who am I?", "The letter 'E'"),
    ("I appear in North, East yet in Uranus, Venus I'm gone. Who am I?", "The letter 'T'"),
    ("In Circle, Oval, Triangle I'm there; in Pentagon, Rhombus I disappear. Who am I?", "The letter 'L'"),
    ("In Nitrogen I'm there; in Peach, Mango I disappear. Who am I?", "The letter 'I'"),
    ("In Pink I'm there; in Blue, White I disappear. Who am I?", "The letter 'N'"),
    ("In Green I'm there; in Apple, Papaya I disappear. Who am I?", "The letter 'R'"),
    ("I appear in Mars yet in Mercury, Jupiter I'm gone. Who am I?", "The letter 'S'"),
    ("In Monday, Thursday I'm there; in North, East, West I disappear. Who am I?", "The letter 'D'"),
    ("You'll find me in all of East but in none of Antarctica, America. What am I?", "The letter 'S'"),
    ("You'll find me in all of South, North but in none of Center. What am I?", "The letter 'H'"),
    ("I'm present in every letter of December, absent from Monkey, Tiger. What am I?", "The letter 'B'"),
    ("You'll find me in all of Plum but in none of South, Center, East. What am I?", "The letter 'P'"),
    ("I appear in Flute yet in Saturn I'm gone. Who am I?", "The letter 'F'"),
    ("You'll find me in all of Rugby but in none of Hockey, Football. What am I?", "The letter 'G'"),
    ("I appear in Clarinet yet in Saturday I'm gone. Who am I?", "The letter 'I'"),
    ("You'll find me in all of Carbon but in none of Nitrogen, Sulfur, Silver. What am I?", "The letter 'A'"),
    ("In Kiwi I'm there; in Earth I disappear. Who am I?", "The letter 'K'"),
    ("I'm present in every letter of Basketball, absent from Thursday. What am I?", "The letter 'K'"),
    ("I'm present in every letter of Thursday, Friday, Wednesday, Monday, absent from Soccer. What am I?", "The letter 'Y'"),
    ("Spot me in Rugby; you won't find me in Football, Basketball, Baseball. What am I?", "The letter 'R'"),
    ("I appear in West yet in Guitar, Clarinet, Harp I'm gone. Who am I?", "The letter 'W'"),
    ("You'll find me in all of Violin but in none of Golf. What am I?", "The letter 'V'"),
    ("You'll find me in all of Cricket, Basketball but in none of Soccer. What am I?", "The letter 'K'"),
    ("Spot me in Bear, Tiger; you won't find me in Monkey. What am I?", "The letter 'R'"),
    ("I'm present in every letter of October, March, November, absent from East, South. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Tennis, absent from Sunday, Friday. What am I?", "The letter 'T'"),
    ("You'll find me in all of Green but in none of Gray, Pink. What am I?", "The letter 'E'"),
    ("You'll find me in all of Venus but in none of Mars, Jupiter, Earth. What am I?", "The letter 'N'"),
    ("I appear in Harp, Drum, Trumpet yet in Kiwi I'm gone. Who am I?", "The letter 'R'"),
    ("I appear in America yet in Mars, Earth I'm gone. Who am I?", "The letter 'C'"),
    ("I'm present in every letter of Monday, absent from Sunday, Tuesday, Saturday. What am I?", "The letter 'M'"),
    ("I'm present in every letter of Peach, absent from Trumpet. What am I?", "The letter 'A'"),
    ("You'll find me in all of North but in none of Center, East. What am I?", "The letter 'O'"),
    ("In Papaya I'm there; in Lemon, Mango, Lime, Grape, Plum I disappear. Who am I?", "The letter 'Y'"),
    ("I'm present in every letter of Mercury, absent from Neptune, Uranus, Venus, Saturn. What am I?", "The letter 'M'"),
    ("You'll find me in all of Nitrogen but in none of White, Yellow, Pink, Brown. What am I?", "The letter 'G'"),
    ("Spot me in Whale; you won't find me in Bear, Otter, Eagle. What am I?", "The letter 'H'"),
    ("I appear in Pear, Apple yet in Blue I'm gone. Who am I?", "The letter 'A'"),
    ("In Tennis I'm there; in Green, Brown, Violet I disappear. Who am I?", "The letter 'S'"),
    ("In Center I'm there; in West, East I disappear. Who am I?", "The letter 'N'"),
    ("Spot me in Friday, Wednesday, Tuesday; you won't find me in Papaya, Peach, Grape, Kiwi. What am I?", "The letter 'D'"),
    ("I appear in Oceania yet in Asia, Africa I'm gone. Who am I?", "The letter 'N'"),
    ("Spot me in Indigo; you won't find me in White, Blue, Brown, Green. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Baseball, Soccer, absent from Panda, Rabbit, Tiger, Fox. What am I?", "The letter 'S'"),
    ("I'm present in every letter of Golf, absent from Tin, Helium, Silver, Sulfur. What am I?", "The letter 'G'"),
    ("In December, June I'm there; in August I disappear. Who am I?", "The letter 'E'"),
    ("In Papaya, Cherry I'm there; in Apple, Orange I disappear. Who am I?", "The letter 'Y'"),
    ("I'm present in every letter of Violet, absent from Wednesday, Friday, Sunday. What am I?", "The letter 'V'"),
    ("I appear in White yet in Orange, Violet I'm gone. Who am I?", "The letter 'H'"),
    ("Spot me in Tuesday, Friday, Sunday, Wednesday; you won't find me in Rectangle, Oval, Hexagon, Triangle. What am I?", "The letter 'Y'"),
    ("You'll find me in all of Mango, Grape, Banana but in none of South, Center, North. What am I?", "The letter 'A'"),
    ("I appear in Rabbit yet in Eagle, Shark I'm gone. Who am I?", "The letter 'T'"),
    ("You'll find me in all of South but in none of East, North, West, Center. What am I?", "The letter 'U'"),
    ("Spot me in Grape; you won't find me in Wednesday, Tuesday, Saturday. What am I?", "The letter 'P'"),
    ("You'll find me in all of Trumpet, Guitar but in none of Oceania, Asia, Antarctica, America. What am I?", "The letter 'U'"),
    ("In Triangle I'm there; in Star, Octagon, Pentagon, Rhombus I disappear. Who am I?", "The letter 'L'"),
    ("Spot me in Star, Square; you won't find me in Triangle. What am I?", "The letter 'S'"),
    ("I'm present in every letter of Grape, absent from Banana, Plum. What am I?", "The letter 'E'"),
    ("I'm present in every letter of Saturday, Friday, absent from Wednesday. What am I?", "The letter 'R'"),
    ("In April I'm there; in Soccer, Rugby, Tennis I disappear. Who am I?", "The letter 'P'"),
    ("I'm present in every letter of Cherry, Papaya, absent from Peach, Orange. What am I?", "The letter 'Y'"),
    ("You'll find me in all of Tin, Helium, Nitrogen but in none of Donkey. What am I?", "The letter 'I'"),
    ("I'm present in every letter of Triangle, absent from Saxophone, Drum. What am I?", "The letter 'L'"),
    ("In Saxophone I'm there; in Trumpet, Piano, Harp I disappear. Who am I?", "The letter 'S'"),
    ("You'll find me in all of Thursday but in none of Saturday, Wednesday, Monday. What am I?", "The letter 'H'"),
    ("You'll find me in all of Venus but in none of Saturday. What am I?", "The letter 'E'"),
    ("Spot me in Orange; you won't find me in Blue, Green, Red, Indigo, White. What am I?", "The letter 'A'"),
    ("I appear in Gray, Black yet in October, June, November I'm gone. Who am I?", "The letter 'A'"),
    ("In Venus, Neptune, Jupiter I'm there; in Saturn I disappear. Who am I?", "The letter 'E'"),
    ("Spot me in Uranus, Mercury, Jupiter, Saturn; you won't find me in Soccer, Golf. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Violin, absent from Wednesday, Monday, Saturday, Thursday. What am I?", "The letter 'V'"),
    ("Spot me in Rectangle; you won't find me in Giraffe, Fox. What am I?", "The letter 'N'"),
    ("I'm present in every letter of Pink, Black, absent from Red, Green. What am I?", "The letter 'K'"),
    ("I appear in Rugby, Baseball yet in Panda, Moose, Shark, Tiger I'm gone. Who am I?", "The letter 'B'"),
    ("In Africa, America I'm there; in Asia I disappear. Who am I?", "The letter 'R'"),
    ("I'm present in every letter of Giraffe, absent from Monkey, Lion, Wolf, Fox. What am I?", "The letter 'R'"),
    ("You'll find me in all of Europe, Oceania but in none of Guitar. What am I?", "The letter 'E'"),
    ("In Orange I'm there; in Pear, Peach I disappear. Who am I?", "The letter 'O'"),
    ("I'm present in every letter of Oval, absent from Hexagon, Rectangle, Rhombus, Pentagon. What am I?", "The letter 'V'"),
    ("I appear in North, East, South, Center yet in Baseball I'm gone. Who am I?", "The letter 'T'"),
    ("You'll find me in all of Europe, Africa, Antarctica but in none of Sunday. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Oval, Triangle, Circle, absent from South, West, Center, East. What am I?", "The letter 'L'"),
    ("I'm present in every letter of Mercury, Mars, absent from Venus, Uranus. What am I?", "The letter 'M'"),
    ("In South, Center I'm there; in Papaya, Grape I disappear. Who am I?", "The letter 'T'"),
    ("I'm present in every letter of Carbon, Iron, Silver, absent from Helium. What am I?", "The letter 'R'"),
    ("I'm present in every letter of Lemon, absent from Lime, Plum, Kiwi, Peach, Pear. What am I?", "The letter 'N'"),
    ("I'm present in every letter of Saturn, Neptune, Venus, absent from Mercury, Mars. What am I?", "The letter 'N'"),
    ("Spot me in August; you won't find me in March, May, January. What am I?", "The letter 'S'"),
    ("I'm present in every letter of Neptune, absent from Africa, Oceania. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Oxygen, Helium, absent from Iron, Carbon. What am I?", "The letter 'E'"),
    ("I appear in May yet in Violin, Drum, Cello I'm gone. Who am I?", "The letter 'Y'"),
    ("You'll find me in all of Friday, Thursday but in none of Guitar, Drum. What am I?", "The letter 'Y'"),
    ("You'll find me in all of Sunday but in none of Red, Yellow. What am I?", "The letter 'N'"),
    ("I'm present in every letter of Circle, absent from Guitar, Piano, Drum. What am I?", "The letter 'L'"),
    ("I'm present in every letter of Monday, absent from Venus, Mercury, Jupiter. What am I?", "The letter 'A'"),
    ("I'm present in every letter of Banana, absent from Pear, Mango. What am I?", "The letter 'B'"),
    ("In Violet, Orange I'm there; in Red I disappear. Who am I?", "The letter 'O'"),
    ("You'll find me in all of Friday but in none of Venus, Jupiter. What am I?", "The letter 'F'"),
    ("Spot me in Papaya; you won't find me in America, Antarctica. What am I?", "The letter 'P'"),
    ("You'll find me in all of December, October, November but in none of Clarinet, Saxophone, Drum. What am I?", "The letter 'B'"),
    ("I'm present in every letter of Clarinet, absent from Cherry, Lemon, Kiwi, Peach. What am I?", "The letter 'T'"),
    ("I appear in Basketball, Hockey, Cricket yet in Sulfur, Nitrogen, Tin, Lead I'm gone. Who am I?", "The letter 'K'"),
    ("I'm present in every letter of Guitar, absent from Volleyball, Soccer, Football. What am I?", "The letter 'U'"),
    ("Spot me in Gray, Red, Orange; you won't find me in Pink. What am I?", "The letter 'R'"),
    ("I appear in Jupiter yet in Venus, Mars, Uranus, Neptune I'm gone. Who am I?", "The letter 'I'"),
    ("You'll find me in all of Circle, Triangle but in none of Blue. What am I?", "The letter 'I'"),
    ("Spot me in Tuesday, Saturday, Friday; you won't find me in South, West, East. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Africa, absent from Antarctica, America. What am I?", "The letter 'F'"),
    ("I appear in Grape, Pear yet in Plum, Banana I'm gone. Who am I?", "The letter 'R'"),
    ("Spot me in Violin, Guitar; you won't find me in Monday, Wednesday. What am I?", "The letter 'I'"),
    ("In Sunday, Wednesday I'm there; in Mango, Plum, Kiwi, Banana I disappear. Who am I?", "The letter 'D'"),
    ("You'll find me in all of West, East but in none of North. What am I?", "The letter 'E'"),
    ("I'm present in every letter of Oxygen, Hydrogen, Tin, absent from Gold. What am I?", "The letter 'N'"),
    ("I'm present in every letter of Yellow, absent from Red, Indigo, Violet, Green. What am I?", "The letter 'Y'"),
    ("Spot me in Rugby, Volleyball; you won't find me in Earth, Mercury, Neptune. What am I?", "The letter 'B'"),
    ("In Soccer I'm there; in West, North, South I disappear. Who am I?", "The letter 'C'"),
    ("Spot me in Basketball, Rugby; you won't find me in Golf, Soccer, Tennis. What am I?", "The letter 'B'"),
    ("In Eagle I'm there; in Rugby I disappear. Who am I?", "The letter 'A'"),
    ("You'll find me in all of Africa, America, Asia but in none of Violin, Cello, Flute. What am I?", "The letter 'A'"),
    ("In Plum, Apple, Lime I'm there; in Orange I disappear. Who am I?", "The letter 'L'"),
    ("I'm present in every letter of Triangle, Circle, Square, absent from Rhombus. What am I?", "The letter 'E'"),
    ("In Center, East, South, North I'm there; in Rugby I disappear. Who am I?", "The letter 'T'"),
    ("In Apple I'm there; in Soccer, Golf, Tennis, Baseball I disappear. Who am I?", "The letter 'P'"),
    ("Spot me in Harp, Clarinet; you won't find me in Violin, Saxophone, Flute, Cello. What am I?", "The letter 'R'"),
    ("I appear in Yak yet in Jupiter, Earth, Saturn I'm gone. Who am I?", "The letter 'K'"),
    ("You'll find me in all of Hexagon, Rectangle but in none of West. What am I?", "The letter 'N'"),
    ("Spot me in Tuesday; you won't find me in Saturday, Thursday, Friday. What am I?", "The letter 'E'"),
    ("Spot me in Mercury, Saturn, Neptune; you won't find me in Green. What am I?", "The letter 'U'"),
    ("You'll find me in all of Uranus but in none of Hydrogen, Helium, Tin, Iron. What am I?", "The letter 'A'"),
    ("I appear in Oceania, America yet in Guitar I'm gone. Who am I?", "The letter 'C'"),
    ("In Sunday I'm there; in Square, Rectangle I disappear. Who am I?", "The letter 'D'"),
    ("I'm present in every letter of Hockey, Cricket, absent from Tennis. What am I?", "The letter 'C'"),
    ("Spot me in Monday; you won't find me in Sunday, Tuesday, Saturday, Thursday, Wednesday, Friday. What am I?", "The letter 'M'"),
    ("I'm present in every letter of Basketball, Volleyball, Cricket, Soccer, absent from Football. What am I?", "The letter 'E'"),
    ("Spot me in Grape, Pear; you won't find me in Orange, Kiwi. What am I?", "The letter 'P'"),
    ("I'm present in every letter of Clarinet, absent from Piano, Flute. What am I?", "The letter 'R'"),
    ("In East, South, West I'm there; in Center, North I disappear. Who am I?", "The letter 'S'"),
    ("You'll find me in all of Wednesday but in none of Saturday, Tuesday. What am I?", "The letter 'N'"),
    ("You'll find me in all of Violin but in none of Piano, Drum, Cello, Flute, Saxophone, Guitar. What am I?", "The letter 'V'"),
    ("In Earth, Mercury, Venus I'm there; in Mars I disappear. Who am I?", "The letter 'E'"),
    ("I'm present in every letter of Africa, Europe, absent from Oceania. What am I?", "The letter 'R'"),
    ("I appear in Wolf, Whale yet in Yak, Tiger, Otter, Shark, Panda I'm gone. Who am I?", "The letter 'W'"),
    ("You'll find me in all of South but in none of Mango, Grape, Lemon. What am I?", "The letter 'H'"),
    ("I appear in Drum yet in Center, East, North I'm gone. Who am I?", "The letter 'M'"),
    ("I'm present in every letter of Hexagon, absent from Wednesday, Monday, Friday. What am I?", "The letter 'H'"),
    ("I appear in Neptune yet in Jupiter, Earth I'm gone. Who am I?", "The letter 'N'"),
    ("I'm present in every letter of Clarinet, absent from Violin, Harp. What am I?", "The letter 'E'"),
    ("Spot me in Earth, Jupiter; you won't find me in Venus. What am I?", "The letter 'T'"),
    ("I'm present in every letter of Earth, absent from Jupiter, Uranus, Mercury, Neptune, Venus. What am I?", "The letter 'H'"),
    ("Spot me in Jupiter, Earth; you won't find me in Neptune. What am I?", "The letter 'R'"),
    ("In December I'm there; in June, January, March, February I disappear. Who am I?", "The letter 'D'"),
    ("Spot me in Thursday, Sunday, Tuesday; you won't find me in Volleyball, Basketball, Cricket. What am I?", "The letter 'U'"),
    ("I'm present in every letter of October, absent from August, July, May. What am I?", "The letter 'C'"),
    ("Spot me in Drum; you won't find me in Flute, Cello, Harp, Violin, Trumpet. What am I?", "The letter 'D'"),
    ("I appear in July yet in Lime, Pear, Kiwi, Banana I'm gone. Who am I?", "The letter 'Y'"),
    ("I appear in Thursday yet in Saturday, Monday, Wednesday, Friday I'm gone. Who am I?", "The letter 'H'"),
    ("Spot me in Banana, Pear; you won't find me in West, Center, South, North. What am I?", "The letter 'A'"),
    ("Spot me in Soccer; you won't find me in Panda, Eagle. What am I?", "The letter 'R'"),
    ("Spot me in Harp; you won't find me in Flute, Piano, Trumpet. What am I?", "The letter 'H'"),
    ("Spot me in Copper, Carbon; you won't find me in Antarctica, America. What am I?", "The letter 'O'"),
    ("You'll find me in all of Lead, Helium but in none of Banana, Kiwi, Papaya. What am I?", "The letter 'E'"),
    ("In Mercury I'm there; in Oceania I disappear. Who am I?", "The letter 'R'"),
    ("In Basketball I'm there; in Tennis, Volleyball, Baseball I disappear. Who am I?", "The letter 'K'"),
    ("I appear in Oval yet in Circle, Hexagon, Rectangle I'm gone. Who am I?", "The letter 'V'"),
    ("I appear in South yet in West, North I'm gone. Who am I?", "The letter 'U'"),
    ("You'll find me in all of Sulfur but in none of Lemon, Banana. What am I?", "The letter 'F'"),
    ("I appear in Thursday, Saturday yet in Violin, Flute, Trumpet I'm gone. Who am I?", "The letter 'D'"),
    ("In Friday, Sunday I'm there; in Basketball I disappear. Who am I?", "The letter 'D'"),
    ("You'll find me in all of Wednesday, Saturday, Monday, Tuesday but in none of Neptune, Venus. What am I?", "The letter 'Y'"),
    ("Spot me in Baseball, Tennis; you won't find me in Football. What am I?", "The letter 'E'"),
    ("In Golf I'm there; in Friday, Thursday, Tuesday, Saturday I disappear. Who am I?", "The letter 'O'"),
    ("I'm present in every letter of Violin, absent from Friday, Sunday, Monday. What am I?", "The letter 'L'"),
    ("You'll find me in all of Africa but in none of Oceania, America, Europe. What am I?", "The letter 'F'"),
    ("In Friday I'm there; in Tuesday, Wednesday, Monday, Sunday, Saturday, Thursday I disappear. Who am I?", "The letter 'F'"),
    ("I'm present in every letter of Whale, absent from Panda, Shark, Rabbit. What am I?", "The letter 'E'"),
    ("You'll find me in all of Oceania but in none of Africa, America, Europe. What am I?", "The letter 'N'"),
    ("I appear in Violet yet in Lemon, Grape, Pear I'm gone. Who am I?", "The letter 'I'"),
    ("You'll find me in all of Gold, Iron, Copper but in none of Silver. What am I?", "The letter 'O'"),
    ("In Africa, America, Antarctica I'm there; in Bear, Wolf, Yak I disappear. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Saturday, Monday, Tuesday, Thursday, absent from Square, Octagon, Circle. What am I?", "The letter 'D'"),
    ("In East I'm there; in Cello, Guitar, Drum I disappear. Who am I?", "The letter 'S'"),
    ("Spot me in Copper; you won't find me in Lead, Iron. What am I?", "The letter 'C'"),
    ("In Iron I'm there; in Copper, Lead, Carbon, Sulfur, Hydrogen I disappear. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Brown, Orange, absent from Violet. What am I?", "The letter 'N'"),
    ("I appear in Tuesday, Saturday yet in Plum, Apple, Banana, Lemon I'm gone. Who am I?", "The letter 'Y'"),
    ("In Wednesday, Thursday I'm there; in Football, Golf I disappear. Who am I?", "The letter 'D'"),
    ("I'm present in every letter of Peach, absent from Orange, Cherry. What am I?", "The letter 'P'"),
    ("You'll find me in all of June, July but in none of October, September. What am I?", "The letter 'U'"),
    ("Spot me in Helium; you won't find me in Gold, Oxygen, Iron, Carbon. What am I?", "The letter 'H'"),
    ("You'll find me in all of Neptune but in none of Drum, Violin. What am I?", "The letter 'P'"),
    ("In Saturday, Tuesday, Wednesday, Monday I'm there; in Drum, Violin I disappear. Who am I?", "The letter 'A'"),
    ("In September, April I'm there; in West I disappear. Who am I?", "The letter 'R'"),
    ("Spot me in Wednesday, Saturday; you won't find me in Rectangle, Octagon, Triangle, Hexagon. What am I?", "The letter 'S'"),
    ("I'm present in every letter of America, Asia, absent from Lead. What am I?", "The letter 'I'"),
    ("In Yellow I'm there; in Wolf, Lion, Eagle, Moose I disappear. Who am I?", "The letter 'Y'"),
    ("You'll find me in all of Volleyball but in none of Neptune, Saturn, Uranus. What am I?", "The letter 'Y'"),
    ("I'm present in every letter of Jupiter, absent from Europe. What am I?", "The letter 'T'"),
    ("You'll find me in all of Iron but in none of Gold, Lead, Copper. What am I?", "The letter 'N'"),
    ("I appear in Neptune yet in Saturn, Venus, Mars I'm gone. Who am I?", "The letter 'P'"),
    ("You'll find me in all of Oxygen, Nitrogen but in none of Gold, Helium, Lead, Silver. What am I?", "The letter 'N'"),
    ("You'll find me in all of Harp, Trumpet but in none of Venus. What am I?", "The letter 'R'"),
    ("In Panda I'm there; in Otter, Monkey, Rabbit I disappear. Who am I?", "The letter 'D'"),
    ("I'm present in every letter of Bear, absent from Tiger, Moose, Eagle, Fox, Lion. What am I?", "The letter 'B'"),
    ("Spot me in Drum, Flute, Trumpet; you won't find me in Hexagon, Star. What am I?", "The letter 'U'"),
    ("I appear in Saturn, Neptune yet in Venus I'm gone. Who am I?", "The letter 'T'"),
    ("I appear in Center, South, West, North yet in Copper, Lead, Hydrogen I'm gone. Who am I?", "The letter 'T'"),
    ("Spot me in Wednesday; you won't find me in North. What am I?", "The letter 'Y'"),
    ("You'll find me in all of July, February, January but in none of December, November. What am I?", "The letter 'Y'"),
    ("I'm present in every letter of Hexagon, absent from Rectangle, Oval, Rhombus, Octagon, Circle, Square. What am I?", "The letter 'X'"),
    ("In Golf, Volleyball I'm there; in Antarctica, Oceania, Asia I disappear. Who am I?", "The letter 'L'"),
    ("I'm present in every letter of Baseball, absent from Golf, Hockey. What am I?", "The letter 'B'"),
    ("In Wednesday, Friday, Monday I'm there; in Piano, Clarinet I disappear. Who am I?", "The letter 'D'"),
    ("Spot me in Clarinet; you won't find me in Harp, Cello. What am I?", "The letter 'T'"),
    ("I'm present in every letter of September, January, February, absent from Venus. What am I?", "The letter 'R'"),
    ("You'll find me in all of Papaya but in none of Peach, Mango. What am I?", "The letter 'Y'"),
    ("I'm present in every letter of Center, absent from Violin. What am I?", "The letter 'R'"),
    ("Spot me in July; you won't find me in Hydrogen. What am I?", "The letter 'L'"),
    ("In Jupiter I'm there; in Mercury, Saturn I disappear. Who am I?", "The letter 'J'"),
    ("You'll find me in all of Sunday, Wednesday, Thursday but in none of Silver, Tin. What am I?", "The letter 'D'"),
    ("Spot me in Helium, Sulfur; you won't find me in Tin, Iron, Lead. What am I?", "The letter 'U'"),
    ("In Bear, Zebra I'm there; in Whale, Monkey, Panda, Giraffe I disappear. Who am I?", "The letter 'B'"),
    ("I'm present in every letter of Nitrogen, absent from Iron, Tin, Sulfur. What am I?", "The letter 'E'"),
    ("Spot me in Sulfur; you won't find me in Lead, Hydrogen, Silver. What am I?", "The letter 'F'"),
    ("In August I'm there; in Tennis, Hockey I disappear. Who am I?", "The letter 'U'"),
    ("I appear in Antarctica yet in Rugby, Football I'm gone. Who am I?", "The letter 'I'"),
    ("I appear in Africa yet in Lead I'm gone. Who am I?", "The letter 'I'"),
    ("In North, Center, West I'm there; in Hockey, Baseball I disappear. Who am I?", "The letter 'T'"),
    ("In Pear I'm there; in Mango, Lime, Banana I disappear. Who am I?", "The letter 'R'"),
    ("Spot me in Jupiter; you won't find me in Saturday, Wednesday. What am I?", "The letter 'J'"),
    ("You'll find me in all of Papaya, Peach but in none of Cherry, Orange, Lime. What am I?", "The letter 'P'"),
    ("I'm present in every letter of Saturday, Thursday, absent from Center, North, West, East. What am I?", "The letter 'D'"),
    ("In Mercury, Neptune I'm there; in Uranus, Saturn I disappear. Who am I?", "The letter 'E'"),
    ("I appear in Harp, Clarinet, Piano yet in Cello, Violin, Trumpet I'm gone. Who am I?", "The letter 'A'"),
    ("I'm present in every letter of Nitrogen, absent from Wednesday, Tuesday, Monday, Sunday. What am I?", "The letter 'R'"),
    ("In Otter I'm there; in Wolf, Fox I disappear. Who am I?", "The letter 'T'"),
    ("Spot me in East; you won't find me in Europe. What am I?", "The letter 'S'"),
    ("In Square I'm there; in North, West, South I disappear. Who am I?", "The letter 'Q'"),
    ("I appear in Lead yet in Tiger, Bear, Fox I'm gone. Who am I?", "The letter 'D'"),
    ("Spot me in Mars, Mercury; you won't find me in Neptune, Jupiter, Earth. What am I?", "The letter 'M'"),
    ("I appear in North yet in Tiger I'm gone. Who am I?", "The letter 'N'"),
    ("In Eagle, Bear, Zebra I'm there; in December, June I disappear. Who am I?", "The letter 'A'"),
    ("I appear in Oxygen yet in Wednesday, Tuesday, Thursday, Sunday I'm gone. Who am I?", "The letter 'O'"),
    ("I appear in Rectangle, Pentagon yet in Saturn, Earth I'm gone. Who am I?", "The letter 'G'"),
    ("I appear in Triangle, Hexagon yet in Oceania I'm gone. Who am I?", "The letter 'G'"),
    ("I'm present in every letter of Cobra, absent from Trumpet. What am I?", "The letter 'A'"),
    ("In Indigo, Pink I'm there; in Yellow I disappear. Who am I?", "The letter 'I'"),
    ("In Cello, Saxophone I'm there; in August, December I disappear. Who am I?", "The letter 'O'"),
    ("You'll find me in all of South, East, West but in none of Giraffe, Otter. What am I?", "The letter 'S'"),
    ("I appear in Silver yet in Fox, Wolf I'm gone. Who am I?", "The letter 'E'"),
    ("Spot me in Jupiter; you won't find me in Neptune, Uranus. What am I?", "The letter 'J'"),
    ("I'm present in every letter of North, South, absent from Center. What am I?", "The letter 'H'"),
    ("Spot me in Saturday; you won't find me in Cherry, Apple. What am I?", "The letter 'D'"),
    ("I'm present in every letter of Guitar, Clarinet, Trumpet, absent from April, November, July. What am I?", "The letter 'T'"),
    ("In Europe I'm there; in Asia, Oceania I disappear. Who am I?", "The letter 'P'"),
    ("You'll find me in all of Gray but in none of Mars. What am I?", "The letter 'G'"),
    ("You'll find me in all of West, East, South but in none of Monday. What am I?", "The letter 'T'"),
    ("Spot me in Yak; you won't find me in Hydrogen, Silver, Iron. What am I?", "The letter 'K'"),
    ("I appear in November yet in Sunday, Thursday I'm gone. Who am I?", "The letter 'O'"),
    ("In Grape, Papaya, Banana, Pear, Apple I'm there; in Cherry I disappear. Who am I?", "The letter 'A'"),
    ("I'm present in every letter of Sunday, absent from Octagon, Circle, Rectangle, Star. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Africa, America, absent from December, January, October. What am I?", "The letter 'I'"),
    ("Spot me in Mango; you won't find me in Oval, Circle. What am I?", "The letter 'N'"),
    ("I'm present in every letter of Lime, Pear, Peach, absent from Kiwi, Papaya. What am I?", "The letter 'E'"),
    ("I'm present in every letter of Jupiter, absent from Mercury, Venus. What am I?", "The letter 'T'"),
    ("I appear in West, North, East yet in Yellow, Black, Indigo I'm gone. Who am I?", "The letter 'T'"),
    ("You'll find me in all of Hydrogen but in none of Green, Black, White, Violet. What am I?", "The letter 'Y'"),
    ("In America I'm there; in Oceania, Antarctica, Europe I disappear. Who am I?", "The letter 'M'"),
    ("You'll find me in all of Friday but in none of Thursday, Tuesday, Wednesday. What am I?", "The letter 'F'"),
    ("Spot me in Antarctica, Asia, America; you won't find me in Europe. What am I?", "The letter 'A'"),
    ("I appear in Europe yet in Africa, Oceania, Antarctica, America I'm gone. Who am I?", "The letter 'U'"),
    ("In Harp, Clarinet I'm there; in Hydrogen I disappear. Who am I?", "The letter 'A'"),
    ("Spot me in Nitrogen, Silver, Tin, Iron; you won't find me in Banana, Apple, Orange. What am I?", "The letter 'I'"),
    ("You'll find me in all of Flute but in none of Pear, Lime, Apple. What am I?", "The letter 'U'"),
    ("Spot me in Hockey; you won't find me in Cricket, Rugby, Soccer, Golf, Tennis. What am I?", "The letter 'H'"),
    ("You'll find me in all of Zebra but in none of Cobra, Eagle, Rabbit, Panda. What am I?", "The letter 'Z'"),
    ("I'm present in every letter of Hockey, absent from Pentagon. What am I?", "The letter 'H'"),
    ("I'm present in every letter of Black, Yellow, absent from Gray, Green. What am I?", "The letter 'L'"),
    ("In Center I'm there; in West, South, North, East I disappear. Who am I?", "The letter 'C'"),
    ("I'm present in every letter of Banana, absent from Apple, Lemon, Peach, Plum, Grape. What am I?", "The letter 'B'"),
    ("I appear in Volleyball, Hockey, Rugby yet in Earth I'm gone. Who am I?", "The letter 'Y'"),
    ("Spot me in South; you won't find me in North, Center, West. What am I?", "The letter 'U'"),
    ("You'll find me in all of Moose but in none of Gold, Hydrogen, Sulfur. What am I?", "The letter 'M'"),
    ("Spot me in Thursday; you won't find me in East, West, South. What am I?", "The letter 'R'"),
    ("I'm present in every letter of America, absent from Zebra, Cobra, Donkey. What am I?", "The letter 'I'"),
    ("In Silver, Nitrogen I'm there; in Copper I disappear. Who am I?", "The letter 'I'"),
    ("I'm present in every letter of Square, Octagon, Rectangle, Oval, absent from White, Blue. What am I?", "The letter 'A'"),
    ("Spot me in Tin; you won't find me in Helium, Lead, Oxygen, Copper. What am I?", "The letter 'T'"),
    ("Spot me in Thursday; you won't find me in Lead, Silver, Tin. What am I?", "The letter 'Y'"),
    ("You'll find me in all of Helium but in none of Hexagon, Star, Pentagon, Rectangle. What am I?", "The letter 'M'"),
    ("In Nitrogen I'm there; in Violet, Brown, White, Pink I disappear. Who am I?", "The letter 'G'"),
    ("You'll find me in all of Sunday, Wednesday but in none of Friday. What am I?", "The letter 'S'"),
    ("You'll find me in all of Black but in none of Blue, Red, Brown. What am I?", "The letter 'C'"),
    ("Spot me in Saxophone; you won't find me in Golf, Hockey, Cricket. What am I?", "The letter 'A'"),
    ("Spot me in South; you won't find me in Saxophone. What am I?", "The letter 'U'"),
    ("In Clarinet I'm there; in January, June, May, April I disappear. Who am I?", "The letter 'T'"),
    ("In Star I'm there; in Oceania, America I disappear. Who am I?", "The letter 'T'"),
    ("Spot me in January; you won't find me in March, February. What am I?", "The letter 'J'"),
    ("You'll find me in all of Baseball, Basketball, Soccer but in none of Cricket, Golf, Volleyball. What am I?", "The letter 'S'"),
    ("Spot me in Rugby; you won't find me in Basketball, Hockey, Football. What am I?", "The letter 'R'"),
    ("In Hydrogen I'm there; in Gray, Yellow I disappear. Who am I?", "The letter 'N'"),
    ("You'll find me in all of Giraffe but in none of Jupiter, Saturn. What am I?", "The letter 'F'"),
    ("I appear in Clarinet yet in South, West, Center, East I'm gone. Who am I?", "The letter 'I'"),
    ("You'll find me in all of January, July but in none of September, May. What am I?", "The letter 'U'"),
    ("Spot me in Orange; you won't find me in Brown, Green. What am I?", "The letter 'A'"),
    ("In Friday I'm there; in Wolf, Donkey I disappear. Who am I?", "The letter 'R'"),
    ("In Circle, Oval I'm there; in Square, Pentagon I disappear. Who am I?", "The letter 'L'"),
    ("Spot me in Piano; you won't find me in February, May. What am I?", "The letter 'I'"),
    ("You'll find me in all of Tennis but in none of Rugby, Cricket, Basketball, Golf, Baseball, Football. What am I?", "The letter 'N'"),
    ("I appear in Baseball yet in Tennis, Soccer, Rugby I'm gone. Who am I?", "The letter 'A'"),
    ("You'll find me in all of South, East, West, North but in none of Drum, Piano, Saxophone, Violin. What am I?", "The letter 'T'"),
    ("You'll find me in all of Rhombus, Rectangle but in none of Yak. What am I?", "The letter 'R'"),
    ("In Venus, Neptune, Uranus, Jupiter I'm there; in Harp, Saxophone, Clarinet I disappear. Who am I?", "The letter 'U'"),
    ("Spot me in South; you won't find me in December, May, March. What am I?", "The letter 'U'"),
    ("In Star, Circle I'm there; in East, West I disappear. Who am I?", "The letter 'R'"),
    ("In Clarinet I'm there; in Drum, Harp, Cello I disappear. Who am I?", "The letter 'I'"),
    ("In Yellow, Blue I'm there; in Fox I disappear. Who am I?", "The letter 'L'"),
    ("In Apple, Pear I'm there; in Hydrogen, Copper I disappear. Who am I?", "The letter 'A'"),
    ("I appear in November, April, February yet in Tuesday, Monday, Sunday, Wednesday I'm gone. Who am I?", "The letter 'R'"),
    ("I'm present in every letter of Flute, Guitar, absent from Clarinet, Violin. What am I?", "The letter 'U'"),
    ("I appear in Oval yet in Square, Rhombus, Pentagon, Hexagon, Rectangle I'm gone. Who am I?", "The letter 'V'"),
    ("You'll find me in all of Hockey but in none of Football, Golf. What am I?", "The letter 'E'"),
    ("You'll find me in all of Carbon but in none of Soccer. What am I?", "The letter 'A'"),
    ("Spot me in Thursday; you won't find me in Saturday, Sunday, Monday. What am I?", "The letter 'H'"),
    ("In Carbon I'm there; in Gold, Silver, Helium, Nitrogen, Copper I disappear. Who am I?", "The letter 'A'"),
    ("Spot me in Bear; you won't find me in Europe, Africa, Oceania. What am I?", "The letter 'B'"),
    ("I appear in West, North yet in Papaya, Cherry I'm gone. Who am I?", "The letter 'T'"),
    ("I appear in America yet in Africa, Antarctica I'm gone. Who am I?", "The letter 'M'"),
    ("In September I'm there; in June, December, November, August I disappear. Who am I?", "The letter 'P'"),
    ("You'll find me in all of Jupiter but in none of Mercury, Neptune, Mars, Uranus. What am I?", "The letter 'J'"),
    ("I'm present in every letter of Rectangle, absent from Oval, Pentagon. What am I?", "The letter 'C'"),
    ("I appear in North, Center yet in Gray, Pink, Orange, Blue I'm gone. Who am I?", "The letter 'T'"),
    ("I'm present in every letter of Mars, absent from Antarctica, Asia, Europe, Oceania. What am I?", "The letter 'M'"),
    ("In Red, Indigo I'm there; in Volleyball, Baseball, Cricket, Tennis I disappear. Who am I?", "The letter 'D'"),
    ("I appear in Square yet in Mercury, Jupiter, Earth, Uranus I'm gone. Who am I?", "The letter 'Q'"),
    ("In West, East I'm there; in North I disappear. Who am I?", "The letter 'S'"),
    ("I'm present in every letter of Square, Circle, Triangle, absent from Oval, Octagon, Star. What am I?", "The letter 'E'"),
    ("You'll find me in all of Bear, Donkey but in none of Panda. What am I?", "The letter 'E'"),
    ("In Football I'm there; in Cricket, Volleyball, Basketball, Baseball I disappear. Who am I?", "The letter 'F'"),
    ("I appear in Uranus, Saturn, Mars, Mercury yet in Wednesday I'm gone. Who am I?", "The letter 'R'"),
    ("Spot me in Plum, Grape; you won't find me in Lemon, Orange. What am I?", "The letter 'P'"),
    ("You'll find me in all of Antarctica, Oceania but in none of America. What am I?", "The letter 'N'"),
    ("In Blue I'm there; in Cricket, Golf, Baseball, Tennis I disappear. Who am I?", "The letter 'U'"),
    ("You'll find me in all of August but in none of Saturday, Sunday, Friday. What am I?", "The letter 'G'"),
    ("I'm present in every letter of Sulfur, absent from June, July. What am I?", "The letter 'R'"),
    ("I appear in Hockey yet in Volleyball, Basketball, Soccer I'm gone. Who am I?", "The letter 'H'"),
    ("Spot me in South; you won't find me in Orange, Yellow. What am I?", "The letter 'T'"),
    ("In Tiger, Moose, Donkey I'm there; in Panda, Fox I disappear. Who am I?", "The letter 'E'"),
    ("I appear in Mercury yet in Hockey I'm gone. Who am I?", "The letter 'U'"),
    ("In Lemon I'm there; in Pear, Mango I disappear. Who am I?", "The letter 'L'"),
    ("I appear in Earth, Neptune yet in Saturn I'm gone. Who am I?", "The letter 'E'"),
    ("In Oval, Triangle I'm there; in Tin I disappear. Who am I?", "The letter 'A'"),
    ("I'm present in every letter of Neptune, Uranus, absent from Mercury. What am I?", "The letter 'N'"),
    ("Spot me in East, South; you won't find me in Asia, Europe, America. What am I?", "The letter 'T'"),
    ("You'll find me in all of Cherry, Peach but in none of Apple, Mango, Orange, Banana. What am I?", "The letter 'C'"),
    ("You'll find me in all of Green, Blue, Yellow but in none of Asia. What am I?", "The letter 'E'"),
    ("You'll find me in all of Triangle, Octagon but in none of Asia, Europe. What am I?", "The letter 'N'"),
    ("Spot me in Carbon; you won't find me in Blue. What am I?", "The letter 'N'"),
    ("You'll find me in all of Europe but in none of Eagle, Wolf, Panda, Otter. What am I?", "The letter 'U'"),
    ("I'm present in every letter of Europe, absent from Oceania, America. What am I?", "The letter 'P'"),
    ("In Thursday, Friday, Tuesday, Sunday I'm there; in Moose, Shark, Giraffe, Fox I disappear. Who am I?", "The letter 'Y'"),
    ("In Mercury, Jupiter I'm there; in Basketball, Hockey, Football I disappear. Who am I?", "The letter 'U'"),
    ("I'm present in every letter of Harp, absent from Guitar, Flute, Piano, Cello. What am I?", "The letter 'H'"),
    ("Spot me in Golf; you won't find me in Tennis, Basketball, Baseball, Soccer, Cricket. What am I?", "The letter 'G'"),
    ("In Pink I'm there; in Violet, Black, Yellow, Green, Orange I disappear. Who am I?", "The letter 'P'"),
    ("I'm present in every letter of Mars, Venus, absent from Trumpet, Harp, Flute, Piano. What am I?", "The letter 'S'"),
    ("In West, Center, South, East I'm there; in Apple, Orange I disappear. Who am I?", "The letter 'T'"),
    ("You'll find me in all of February but in none of January, July, May. What am I?", "The letter 'B'"),
    ("In Yak I'm there; in Saxophone I disappear. Who am I?", "The letter 'K'"),
    ("I'm present in every letter of Saxophone, Violin, Piano, absent from Drum, Harp, Clarinet, Guitar. What am I?", "The letter 'O'"),
    ("In Monday, Friday I'm there; in Lime, Kiwi, Banana I disappear. Who am I?", "The letter 'D'"),
    ("I appear in Rugby, Basketball, Football yet in Tennis, Hockey, Golf I'm gone. Who am I?", "The letter 'B'"),
    ("Spot me in October, January, February; you won't find me in July, May. What am I?", "The letter 'R'"),
    ("You'll find me in all of Asia, Oceania, Africa, America but in none of Rugby, Volleyball, Golf. What am I?", "The letter 'I'"),
    ("You'll find me in all of Antarctica, Africa, America, Asia, Oceania but in none of Europe. What am I?", "The letter 'A'"),
    ("You'll find me in all of Africa but in none of Cricket, Basketball, Baseball, Tennis. What am I?", "The letter 'F'"),
    ("In Donkey, Shark I'm there; in Octagon, Square, Circle I disappear. Who am I?", "The letter 'K'"),
    ("Spot me in Venus, Uranus; you won't find me in Gold, Tin, Hydrogen, Nitrogen. What am I?", "The letter 'S'"),
    ("In Rectangle I'm there; in Mars I disappear. Who am I?", "The letter 'T'"),
    ("I appear in Antarctica, Africa yet in Bear, Monkey, Lion I'm gone. Who am I?", "The letter 'C'"),
    ("In South, East, North I'm there; in Europe I disappear. Who am I?", "The letter 'T'"),
    ("I appear in Violin yet in Drum, Cello, Trumpet I'm gone. Who am I?", "The letter 'V'"),
    ("Spot me in Lion; you won't find me in Asia, Africa, Europe. What am I?", "The letter 'L'"),
    ("I'm present in every letter of Oceania, America, absent from Antarctica, Asia. What am I?", "The letter 'E'"),
    ("I appear in Basketball, Tennis yet in Football I'm gone. Who am I?", "The letter 'S'"),
    ("You'll find me in all of Monday, Wednesday but in none of Oceania, Europe, Antarctica, Africa. What am I?", "The letter 'D'"),
    ("I appear in Peach yet in Mango, Orange I'm gone. Who am I?", "The letter 'C'"),
    ("You'll find me in all of Gold but in none of Venus. What am I?", "The letter 'G'"),
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
    batch_duplicates = check_duplicates_in_batch(riddles_batch4)
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

    for i, (question, answer) in enumerate(riddles_batch4):
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
    print(f"- Total riddles in batch: {len(riddles_batch4)}")
    print(f"- Added to database: {added_count}")
    print(f"- Skipped (duplicates): {skipped_duplicates}")
    print(f"- Batch duplicates found: {len(batch_duplicates)}")

if __name__ == "__main__":
    add_riddles_to_db()