"""Cross-story activity variety, vocabulary, and storyboard page mapping."""

from copy import deepcopy


STORYBOARD_PAGE_PANELS = {
    'A Very Hot Day': [1, 3, 5, 6],
    'Ben Goes to School': [1, 2, 3, 5, 6],
    "Olwethu's First Day": [1, 2, 3, 5, 6],
    'Bongi Waits': [1, 3, 4, 5, 6],
    "A Dog's Life": [1, 2, 3, 4, 5, 6],
    'A New Baby': [1, 2, 3, 4, 5, 6],
    'The School Shed Is on Fire': [1, 3, 5, 6],
    "Dan's Bad Week": [1, 2, 3, 4, 5, 6],
    'Spring Day Surprise': [1, 2, 3, 4, 5, 6],
    "Mandu's Secret Diary": [1, 2, 3, 4, 5, 6],
    'Soccer Trouble': [1, 2, 5, 6],
    'The River Mistake': [1, 2, 3, 6],
    'Stage Fright': [1, 3, 4, 5],
    'The Juice Spill': [1, 2, 4, 6],
    "Mandu's Running Shoes": [1, 2, 3, 4, 5],
    'Why Mapula Missed School': [1, 2, 3, 4, 5],
    'Best Friends to the Rescue': [1, 2, 3, 4, 5],
    'The Terrible Twins': [1, 2, 3, 4, 5],
    "Frog and Crow's Wrong Message": [1, 2, 3, 4, 5],
}


VISUAL_VOCAB_SHEETS = {
    'A Very Hot Day': 'g1_hot_vocab.png',
    'Ben Goes to School': 'g1_ben_vocab.png',
    "Olwethu's First Day": 'g1_olwethu_vocab.png',
    'Bongi Waits': 'g1_bongi_vocab.png',
    "A Dog's Life": 'g2_dog_vocab.png',
    'A New Baby': 'g2_baby_vocab.png',
    'The School Shed Is on Fire': 'g2_fire_vocab.png',
    "Dan's Bad Week": 'g2_dan_vocab.png',
    'Spring Day Surprise': 'g2_spring_vocab.png',
    "Mandu's Secret Diary": 'g3_mandu_vocab.png',
    'Soccer Trouble': 'g3_soccer_vocab.png',
    'The River Mistake': 'g3_river_vocab.png',
    'Stage Fright': 'g3_stage_vocab.png',
    'The Juice Spill': 'g3_juice_vocab.png',
    "Mandu's Running Shoes": 'g4_mandu_shoes_vocab.png',
    'Why Mapula Missed School': 'g4_mapula_vocab.png',
    'Best Friends to the Rescue': 'g4_rescue_vocab.png',
    'The Terrible Twins': 'g4_twins_vocab.png',
    "Frog and Crow's Wrong Message": 'g4_message_vocab.png',
}


# Each tuple is (English word, isiZulu word, vocabulary-sheet panel or image URL).
LESSON_WORDS = {
    "Lerato's Fruit Basket": [
        ('Apple', 'Ihhabhula', '/static/img/lerato/fruit_apple.png'),
        ('Banana', 'Ubhanana', '/static/img/lerato/fruit_banana.png'),
        ('Orange', 'I-oranje', '/static/img/lerato/fruit_orange_user.webp'),
        ('Mango', 'Umango', '/static/img/lerato/fruit_mango_user.webp'),
        ('Basket', 'Ubhasikidi', '/static/img/lerato/lerato_basket.png'),
    ],
    'A Very Hot Day': [
        ('Sun', 'Ilanga', 1),
        ('Ball', 'Ibhola', 2),
        ('Pond', 'Ichibi', 3),
        ('Shoes', 'Izicathulo', 4),
        ('Fish', 'Inhlanzi', 5),
    ],
    'Ben Goes to School': [
        ('School', 'Isikole', 1),
        ('Dog', 'Inja', 2),
        ('Backpack', 'Isikhwama sesikole', 3),
        ('Music', 'Umculo', 4),
        ('Ball', 'Ibhola', 5),
    ],
    "Olwethu's First Day": [
        ('Bed', 'Umbhede', 1),
        ('Uniform', 'Umfaniswano', 2),
        ('School', 'Isikole', 3),
        ('Friend', 'Umngane', 4),
        ('Pencil', 'Ipensela', 5),
    ],
    'Bongi Waits': [
        ('Granny', 'Ugogo', 1),
        ('Grandpa', 'Umkhulu', 2),
        ('Rope', 'Intambo', 3),
        ('Book', 'Incwadi', 4),
        ('Braai', 'Ibraai', 5),
    ],
    "A Dog's Life": [
        ('Bus', 'Ibhasi', 1),
        ('Book', 'Incwadi', 2),
        ('Tree', 'Isihlahla', 3),
        ('Cloud', 'Ifu', 4),
        ('Wave', 'Igagasi', 5),
    ],
    'A New Baby': [
        ('Mother', 'Umama', 1),
        ('Father', 'Ubaba', 2),
        ('Hospital', 'Isibhedlela', 3),
        ('Baby', 'Ingane', 4),
        ('Hand', 'Isandla', 5),
    ],
    'The School Shed Is on Fire': [
        ('Smoke', 'Intuthu', 1),
        ('Teacher', 'Uthisha', 2),
        ('Bell', 'Insimbi', 3),
        ('Firefighter', 'Isicishamlilo', 4),
        ('Hose', 'Ipayipi', 5),
    ],
    "Dan's Bad Week": [
        ('Bus', 'Ibhasi', 1),
        ('Bag', 'Isikhwama', 2),
        ('School', 'Isikole', 3),
        ('Uniform', 'Umfaniswano', 4),
        ('Cake', 'Ikhekhe', 5),
    ],
    'Spring Day Surprise': [
        ('Butterfly', 'Uvemvane', 1),
        ('Teacher', 'Uthisha', 2),
        ('Ball', 'Ibhola', 3),
        ('Bucket', 'Ibhakede', 4),
        ('Water', 'Amanzi', 5),
    ],
    "Mandu's Secret Diary": [
        ('Diary', 'Idayari', 1),
        ('Pencil', 'Ipensela', 2),
        ('Fingerprint', 'Isigxivizo somunwe', 3),
        ('Hair', 'Unwele', 4),
        ('Flour', 'Ufulawa', 5),
    ],
    'Soccer Trouble': [
        ('Player', 'Umdlali', 1),
        ('Coach', 'Umqeqeshi', 2),
        ('Whistle', 'Impempe', 3),
        ('Boot', 'Isicathulo sebhola', 4),
        ('Ball', 'Ibhola', 5),
    ],
    'The River Mistake': [
        ('Mother', 'Umama', 1),
        ('River', 'Umfula', 2),
        ('Goat', 'Imbuzi', 3),
        ('Shirt', 'Ihembe', 4),
        ('Leaf', 'Iqabunga', 5),
    ],
    'Stage Fright': [
        ('Wolf', 'Impisi', 1),
        ('Stage', 'Isiteji', 2),
        ('Curtain', 'Ikhethini', 3),
        ('Teacher', 'Uthisha', 4),
        ('House', 'Indlu', 5),
    ],
    'The Juice Spill': [
        ('Exam Paper', 'Iphepha lesivivinyo', 1),
        ('Bottle', 'Ibhodlela', 2),
        ('Teacher', 'Uthisha', 3),
        ('Spill', 'Ukuchitheka', 4),
        ('Principal', 'Uthishanhloko', 5),
    ],
    "Mandu's Running Shoes": [
        ('Running Shoes', 'Izicathulo zokugijima', 1),
        ('Coin', 'Uhlamvu lwemali', 2),
        ('Whistle', 'Impempe', 3),
        ('Track', 'Umzila wokugijima', 4),
        ('Medal', 'Indondo', 5),
    ],
    'Why Mapula Missed School': [
        ('Stove', 'Isitofu', 1),
        ('Matches', 'Umentshisi', 2),
        ('Smoke', 'Intuthu', 3),
        ('Fire Engine', 'Imoto yezicishamlilo', 4),
        ('Hose', 'Ipayipi', 5),
    ],
    'Best Friends to the Rescue': [
        ('First Aid Kit', 'Ibhokisi losizo lokuqala', 1),
        ('Tree', 'Isihlahla', 2),
        ('Gloves', 'Amagilavu', 3),
        ('Bandage', 'Ibhandeshi', 4),
        ('Ambulance', 'I-ambulensi', 5),
    ],
    'The Terrible Twins': [
        ('Mirror', 'Isibuko', 1),
        ('Hat', 'Isigqoko', 2),
        ('Mask', 'Isifihla-buso', 3),
        ('Calendar', 'Ikhalenda', 4),
        ('Uniform', 'Umfaniswano', 5),
    ],
    "Frog and Crow's Wrong Message": [
        ('Crow', 'Igwababa', 1),
        ('Frog', 'Ixoxo', 2),
        ('Message', 'Umlayezo', 3),
        ('Mealies', 'Ummbila', 4),
        ('Basket', 'Ubhasikidi', 5),
    ],
}


PRONUNCIATION_WORDS = {
    "Mandu's Secret Diary": [
        ('Diary', 'Idayari', '/static/img/pronunciation/mandu_secret_diary/diary.png'),
        ('Secret', 'Imfihlo', '/static/img/pronunciation/mandu_secret_diary/secret.png'),
        ('Hide', 'Fihla', '/static/img/pronunciation/mandu_secret_diary/hide.png'),
        ('Clue', 'Umkhondo', '/static/img/pronunciation/mandu_secret_diary/clue.png'),
        ('Blond', 'Izinwele eziphuzi', '/static/img/pronunciation/mandu_secret_diary/blond.png'),
        ('Flour', 'Ufulawa', '/static/img/pronunciation/mandu_secret_diary/flour.png'),
        ('Footprint', 'Umkhondo wonyawo', '/static/img/pronunciation/mandu_secret_diary/footprint.png'),
        ('Culprit', 'Umenzi wobubi', '/static/img/pronunciation/mandu_secret_diary/culprit.png'),
    ],
}


LESSON_SPELLING = {
    "Mandu's Secret Diary": [
        ('d_ary', 'diary'),
        ('b_d', 'bed'),
        ('d_g', 'dog'),
        ('tr_p', 'trap'),
        ('op_n', 'open'),
    ],
}


def _choice(activity_type, skill, question, options, answer):
    return {
        'activity_type': activity_type,
        'skill': skill,
        'question': question,
        'options': options,
        'correct_answer': answer,
    }


def _oral(skill, question, answer):
    return {
        'activity_type': 'oral_response',
        'skill': skill,
        'question': question,
        'correct_answer': answer,
    }


def _written(activity_type, skill, question, answer):
    return {
        'activity_type': activity_type,
        'skill': skill,
        'question': question,
        'correct_answer': answer,
    }


def _sequence(question, items):
    return {
        'activity_type': 'sequencing',
        'skill': 'sequencing',
        'question': question,
        'items_in_correct_order': items,
    }


EXTRA_ACTIVITIES = {
    "Lerato's Fruit Basket": _choice(
        'matching', 'vocabulary_in_context',
        'Which word matches the container that holds Lerato\'s fruit?',
        ['Basket', 'Shoe', 'Plate', 'Cup'], 'Basket',
    ),
    'A Very Hot Day': _choice(
        'cloze', 'literal_comprehension',
        'Karabo cooled down by jumping into the ___.',
        ['pond', 'classroom', 'bus'], 'pond',
    ),
    'Ben Goes to School': _written(
        'prediction', 'prediction',
        'Ben is hiding near the school. What do you think he will do when he sees the ball at break? Give one clue.',
        'Ben will run onto the field and chase the ball because he followed Jabu and likes to play.',
    ),
    "Olwethu's First Day": _choice(
        'matching', 'vocabulary_in_context',
        'Which word matches the special clothes Olwethu wore to school?',
        ['Uniform', 'Blanket', 'Costume', 'Apron'], 'Uniform',
    ),
    'Bongi Waits': _choice(
        'cloze', 'literal_comprehension',
        'Bongi read a picture book to her baby brother, ___.',
        ['Siya', 'Gugu', 'Grandpa'], 'Siya',
    ),
    "A Dog's Life": _oral(
        'text_to_self',
        'How might Ben feel when he has to wait outside? Use one feeling word and a story clue.',
        'Ben may feel lonely or left out because Abby and Lebo go to places without him.',
    ),
    'A New Baby': _choice(
        'true_false', 'literal_comprehension',
        'Bobby wanted a baby brother from the beginning.',
        ['True', 'False'], 'False',
    ),
    'The School Shed Is on Fire': _oral(
        'literal_comprehension',
        'Name one thing the teacher did to keep the learners safe.',
        'The teacher moved the learners away from the shed and phoned the fire service.',
    ),
    "Dan's Bad Week": _choice(
        'cloze', 'literal_comprehension',
        'On Wednesday, Dan got onto the ____ bus.',
        ['wrong', 'empty', 'broken'], 'wrong',
    ),
    'Spring Day Surprise': _choice(
        'matching', 'vocabulary_in_context',
        'Which word means moving quickly?',
        ['Hurried', 'Waited', 'Rested', 'Forgot'], 'Hurried',
    ),
    "Mandu's Secret Diary": _choice(
        'true_false', 'inference',
        'Anna was the one who opened Mandu\'s diary.',
        ['True', 'False'], 'False',
    ),
    'Soccer Trouble': _choice(
        'cloze', 'character_motivation',
        'John tried to ____ Mary instead of listening to Coach Jones.',
        ['impress', 'avoid', 'teach'], 'impress',
    ),
    'The River Mistake': _oral(
        'inference',
        'Name two results of the boys ignoring Mother\'s warning.',
        'Goats damaged their clothes, the boys were put in danger, and Mother was angry.',
    ),
    'Stage Fright': _choice(
        'true_false', 'inference',
        'John forgot his lines because he had not practised.',
        ['True', 'False'], 'False',
    ),
    'The Juice Spill': _choice(
        'matching', 'vocabulary_in_context',
        'Which meaning matches the word permission?',
        ['Being allowed to do something', 'Hiding something', 'Making a mess'], 'Being allowed to do something',
    ),
    'Why Mapula Missed School': _choice(
        'true_false', 'literal_comprehension',
        'Mapula went back inside after taking Thami outdoors.',
        ['True', 'False'], 'False',
    ),
    'Best Friends to the Rescue': _choice(
        'cloze', 'literal_comprehension',
        'The girls asked an adult to call an ____.',
        ['ambulance', 'ice-cream van', 'school bus'], 'ambulance',
    ),
    'The Terrible Twins': _choice(
        'matching', 'vocabulary_in_context',
        'Which item helped Todd and Ted discover the correct date?',
        ['Calendar', 'Mirror', 'Mask', 'Hat'], 'Calendar',
    ),
    "Frog and Crow's Wrong Message": _choice(
        'true_false', 'literal_comprehension',
        'DM and BW were abbreviations on Mrs Hen\'s shopping list.',
        ['True', 'False'], 'True',
    ),
}


ACTIVITY_ORDERS = {
    "Lerato's Fruit Basket": [0, 'extra', 1, 3, 2],
    'A Very Hot Day': ['extra', 0, 2, 1, 3],
    'Ben Goes to School': [1, 0, 'extra', 3, 2],
    "Olwethu's First Day": [0, 2, 'extra', 1, 3],
    'Bongi Waits': [2, 'extra', 0, 1, 3],
    "A Dog's Life": [0, 2, 'extra', 1, 4, 3],
    'A New Baby': [2, 0, 'extra', 1, 4, 3],
    'The School Shed Is on Fire': ['extra', 0, 2, 1, 4, 3],
    "Dan's Bad Week": [0, 'extra', 2, 4, 1, 3],
    'Spring Day Surprise': [1, 0, 'extra', 2, 3, 4],
    "Mandu's Secret Diary": [0, 'extra', 2, 1, 4, 3, 5],
    'Soccer Trouble': [1, 0, 'extra', 2, 3, 4, 5],
    'The River Mistake': [2, 0, 'extra', 1, 3, 5, 4],
    'Stage Fright': ['extra', 0, 1, 2, 3, 4, 5],
    'The Juice Spill': [0, 2, 'extra', 1, 3, 4, 5],
    'Why Mapula Missed School': [0, 1, 'extra', 2, 3, 4, 5, 6],
    'Best Friends to the Rescue': [0, 'extra', 2, 1, 3, 4, 5, 6],
    'The Terrible Twins': [0, 1, 3, 'extra', 2, 4, 5, 6],
    "Frog and Crow's Wrong Message": [0, 2, 'extra', 1, 3, 4, 5, 6],
}


MATCHING_ACTIVITY_INDEX = {
    "A Dog's Life": 1,
    'The School Shed Is on Fire': 1,
    'Spring Day Surprise': 1,
    "Mandu's Secret Diary": 1,
    'The River Mistake': 1,
    'Stage Fright': 1,
    'Why Mapula Missed School': 2,
    'Best Friends to the Rescue': 1,
    'The Terrible Twins': 2,
    "Frog and Crow's Wrong Message": 1,
}


def build_enriched_activities(title, source_activities):
    activities = deepcopy(source_activities)
    if any(activity.get('group_number') for activity in activities):
        return activities
    matching_index = MATCHING_ACTIVITY_INDEX.get(title)
    if matching_index is not None and matching_index < len(activities):
        activities[matching_index]['activity_type'] = 'matching'

    extra = deepcopy(EXTRA_ACTIVITIES.get(title))
    if not extra:
        return activities

    order = ACTIVITY_ORDERS.get(title)
    if not order:
        return activities + [extra]

    return [
        extra if item == 'extra' else activities[item]
        for item in order
    ]
