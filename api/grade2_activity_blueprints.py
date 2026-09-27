"""Every Grade 2 activity, exactly as set out in the Grade 2 Final Activities Spec (v2).

Each story has the same five activity groups, in the same order as the document:

    1. Comprehension Questions   (5)
    2. Match It!                 (1 activity, 4 pairs + 1 decoy)
    3. Visual Matching           (5)
    4. Spelling                  (5)
    5. Fix the Mistake           (5)

Load it into the database with::

    python manage.py sync_grade2_activities

This mirrors api/grade1_activity_blueprints.py: the data lives here, the
management command writes it to the database, and no other file needs editing
when the wording of an activity changes.
"""

import json


# --- Picture sheets -------------------------------------------------------
# Each vocabulary sheet is a 3x2 grid. "#panel-N" crops to one picture,
# numbered left to right, top row first.

VOCAB_SHEETS = {
    "A Dog's Life": '/static/img/vocab_sheets/g2_dog_vocab.png',
    'A New Baby': '/static/img/vocab_sheets/g2_baby_vocab.png',
    'The School Shed Is on Fire': '/static/img/vocab_sheets/g2_fire_vocab.png',
    "Dan's Bad Week": '/static/img/vocab_sheets/g2_dan_vocab.png',
    'Spring Day Surprise': '/static/img/vocab_sheets/g2_spring_vocab.png',
}

# The five picture words on each sheet, in panel order.
STORY_WORDS = {
    "A Dog's Life": ['Bus', 'Book', 'Tree', 'Cloud', 'Wave'],
    'A New Baby': ['Mother', 'Father', 'Hospital', 'Baby', 'Hand'],
    'The School Shed Is on Fire': ['Smoke', 'Teacher', 'Bell', 'Firefighter', 'Hose'],
    "Dan's Bad Week": ['Bus', 'Bag', 'School', 'Uniform', 'Cake'],
    'Spring Day Surprise': ['Butterfly', 'Teacher', 'Ball', 'Bucket', 'Water'],
}


def panel(story, number):
    """Return the image URL for one picture on a story's vocabulary sheet."""
    return f'{VOCAB_SHEETS[story]}#panel-{number}'


def picture_for(story, word):
    """Find the picture for a word, or return '' when the sheet has none."""
    words = [w.lower() for w in STORY_WORDS[story]]
    target = word.lower()
    if target in words:
        return panel(story, words.index(target) + 1)
    return ''


# --- Activity builders ----------------------------------------------------
# Group 1 and 2 numbers follow the document's own numbering, so the learner
# meets the activities in the printed order.

def comprehension(question, options, answer, image=''):
    """1. Comprehension Questions — one multiple-choice question."""
    return {
        'activity_type': 'multiple_choice',
        'skill': 'literal_comprehension',
        'question': question,
        'options': {
            'choices': list(options),
            'audio_text': question,
            'prompt_image': image,
            'instruction': 'Read or listen to the question, then choose the best answer.',
        },
        'correct_answer': answer,
        'group_number': 1,
        'group_title': 'Comprehension Questions',
    }


def match_it(left_items, right_items, pairs):
    """2. Match It! — 4 real pairs plus 1 decoy on the right.

    ``left_items``  the fixed left column, in document order.
    ``right_items`` all five right-hand options, the last one being the decoy.
    ``pairs``       the answer key, as {left text: right text}.
    """
    prompts = [
        {'key': str(index), 'text': text}
        for index, text in enumerate(left_items, start=1)
    ]
    choices = [
        {'key': chr(64 + index), 'text': text}
        for index, text in enumerate(right_items, start=1)
    ]
    text_to_key = {choice['text']: choice['key'] for choice in choices}
    answer_key = {
        prompt['key']: text_to_key[pairs[prompt['text']]]
        for prompt in prompts
    }
    return {
        'activity_type': 'matching',
        'skill': 'literal_comprehension',
        'question': 'Match each one on the left to what happened on the right.',
        'options': {
            'prompts': prompts,
            'choices': choices,
            'audio_text': 'Match each one on the left to what happened on the right.',
            'instruction': 'Match each one on the left to what happened on the right.',
        },
        'correct_answer': json.dumps(answer_key),
        'group_number': 2,
        'group_title': 'Match It!',
    }


def visual_match(story, word, choices):
    """3. Visual Matching — tap the word that matches the picture."""
    return {
        'activity_type': 'multiple_choice',
        'skill': 'vocabulary_in_context',
        'question': 'Tap the word that matches the picture.',
        'options': {
            'choices': list(choices),
            'prompt_image': picture_for(story, word),
            'prompt_alt': word,
            'audio_text': 'Tap the word that matches the picture.',
            'instruction': 'Look at the picture, then choose the word that names it.',
        },
        'correct_answer': word,
        'group_number': 3,
        'group_title': 'Visual Matching',
    }


def fill_vowel(story, display_word, word, choices, answer):
    """4. Spelling — Fill Missing Vowel (pick the letter from 3 options)."""
    return {
        'activity_type': 'cloze',
        'skill': 'spelling',
        'question': f'Complete the word: {display_word}',
        'options': {
            'presentation': 'grade1_phonics',
            'choices': list(choices),
            'audio_text': word,
            'display_word': display_word,
            'prompt_image': picture_for(story, word),
            'prompt_alt': word,
            'instruction': 'Listen to the word and choose the missing letter.',
        },
        'correct_answer': answer,
        'group_number': 4,
        'group_title': 'Spelling',
    }


def unscramble(story, letters, word):
    """4. Spelling — Drag Letters (unscramble the letters into the word)."""
    spaced = ', '.join(letters)
    return {
        'activity_type': 'word_scramble',
        'skill': 'spelling',
        'question': f'Unscramble the letters: {spaced}',
        'options': {
            'items': [{'key': word.lower(), 'scramble': ''.join(letters)}],
            'audio_text': word,
            'prompt_image': picture_for(story, word),
            'prompt_alt': word.title(),
            'instruction': 'Put the letters in the right order and type the word.',
        },
        'correct_answer': json.dumps({word.lower(): word}),
        'group_number': 4,
        'group_title': 'Spelling',
    }


def choose_spelling(story, choices, answer):
    """4. Spelling — Choose the Correct Spelling (multiple choice)."""
    return {
        'activity_type': 'multiple_choice',
        'skill': 'spelling',
        'question': 'Which word is spelled correctly?',
        'options': {
            'choices': list(choices),
            'audio_text': answer,
            'prompt_image': picture_for(story, answer),
            'prompt_alt': answer,
            'instruction': 'Look at the picture and choose the correct spelling.',
        },
        'correct_answer': answer,
        'group_number': 4,
        'group_title': 'Spelling',
    }


def fix_the_mistake(sentence, choices, answer):
    """5. Fix the Mistake — one word has been changed; pick the right one."""
    return {
        'activity_type': 'cloze',
        'skill': 'literal_comprehension',
        'question': sentence,
        'options': {
            'choices': list(choices),
            'audio_text': sentence,
            'instruction': (
                f'One word in this sentence is wrong. '
                f'Choose the word that belongs in the story. {sentence}'
            ),
        },
        'correct_answer': answer,
        'group_number': 5,
        'group_title': 'Fix the Mistake',
    }



# --- A Dog's Life --------------------------------------------------------
A_DOGS_LIFE_ACTIVITIES = [
    # 1. Comprehension Questions (5)
    comprehension(
        "Why couldn't Ben get on the school bus?",
        ['He was too big', 'No dogs allowed', 'He was scared', 'He was sick'],
        'No dogs allowed',
    ),
    comprehension(
        'Where did Ben wait while Abby and Lebo were at the park?',
        ['In the classroom', 'On the bus', 'Under a tree at the gate', 'At the beach'],
        'Under a tree at the gate',
    ),
    comprehension(
        'What did Ben dream about doing at school?',
        ['Riding the bus and sitting in class', 'Cooking dinner', 'Driving a car', 'Reading a book'],
        'Riding the bus and sitting in class',
    ),
    comprehension(
        'What did Ben dream about doing at the beach?',
        ['Digging in the sand and surfing in the waves', 'Fishing all day', 'Building a sandcastle only', 'Sleeping under an umbrella'],
        'Digging in the sand and surfing in the waves',
    ),
    comprehension(
        'What happened when Abby and Lebo came back?',
        ['Ben ran away', 'Ben woke up and realised it was a dream', 'Ben got on the bus', 'Ben cried'],
        'Ben woke up and realised it was a dream',
    ),

    # 2. Match It! (4 pairs + 1 decoy)
    match_it(
        ['Bus', 'Beach', 'Park', 'Dream'],
        [
            'No dogs allowed',
            'Ben could not go with them',
            'Ben waited under a tree',
            'Ben surfed in the waves',
            'Ben could not go inside',  # decoy
        ],
        {
            'Bus': 'No dogs allowed',
            'Beach': 'Ben could not go with them',
            'Park': 'Ben waited under a tree',
            'Dream': 'Ben surfed in the waves',
        },
    ),

    # 4. Visual Matching (5)
    visual_match("A Dog's Life", 'Bus', ['Tree', 'Cloud', 'Wave', 'Bus', 'Book']),
    visual_match("A Dog's Life", 'Book', ['Cloud', 'Wave', 'Bus', 'Book', 'Tree']),
    visual_match("A Dog's Life", 'Tree', ['Wave', 'Bus', 'Book', 'Tree', 'Cloud']),
    visual_match("A Dog's Life", 'Cloud', ['Bus', 'Book', 'Tree', 'Cloud', 'Wave']),
    visual_match("A Dog's Life", 'Wave', ['Book', 'Tree', 'Cloud', 'Wave', 'Bus']),

    # 5. Spelling (5) — Fill Missing Vowel
    fill_vowel("A Dog's Life", 'b_s', 'bus', ['u', 'a', 'o'], 'u'),
    fill_vowel("A Dog's Life", 'b_ok', 'book', ['o', 'a', 'e'], 'o'),
    fill_vowel("A Dog's Life", 'tr_e', 'tree', ['e', 'a', 'o'], 'e'),
    fill_vowel("A Dog's Life", 'cl_ud', 'cloud', ['o', 'a', 'e'], 'o'),
    fill_vowel("A Dog's Life", 'w_ve', 'wave', ['a', 'e', 'i'], 'a'),

    # 6. Fix the Mistake (5)
    fix_the_mistake(
        'Ben could not get onto the car.',
        ['bus', 'van', 'truck'],
        'bus',
    ),
    fix_the_mistake(
        'On Friday, Abby and Lebo went to the beach, but Ben could not go inside.',
        ['library', 'park', 'shop'],
        'library',
    ),
    fix_the_mistake(
        'Ben sat under a table at the gate.',
        ['tree', 'bench', 'wall'],
        'tree',
    ),
    fix_the_mistake(
        'In his dream, Ben rode the car and sat at the front.',
        ['bus', 'taxi', 'train'],
        'bus',
    ),
    fix_the_mistake(
        'Ben opened his eyes and realised his adventure had been a story.',
        ['dream', 'game', 'trick'],
        'dream',
    ),
]


# --- A New Baby ----------------------------------------------------------
A_NEW_BABY_ACTIVITIES = [
    # 1. Comprehension Questions (5)
    comprehension(
        '"Is it a girl or a boy?" — Who asked this?',
        ['Bobby', 'Father', 'Granny', 'Mother'],
        'Bobby',
    ),
    comprehension(
        '"It is a boy." — Who said this?',
        ['Bobby', 'Father', 'Mother', 'Granny'],
        'Father',
    ),
    comprehension(
        '"He is so cute. He looks just like me." — Who said this?',
        ['Granny', 'Father', 'Bobby', 'Mother'],
        'Bobby',
    ),
    comprehension(
        '"I love you just as you are." — Who said this to baby Andy?',
        ['Mother', 'Father', 'Bobby', 'Granny'],
        'Bobby',
    ),
    comprehension(
        '"Granny would look after him while she was in hospital." — Who said this to Bobby?',
        ['Mother', 'Father', 'Granny', 'Andy'],
        'Mother',
    ),

    # 2. Match It! (4 pairs + 1 decoy)
    match_it(
        ['Bobby', 'Mother', 'Father', 'Andy'],
        [
            'Wanted a big brother, not a baby',
            'Went to hospital to have the baby',
            'Told Bobby the baby was a boy',
            'Could not play soccer yet',
            'Looked after Bobby while Mother was away',  # decoy
        ],
        {
            'Bobby': 'Wanted a big brother, not a baby',
            'Mother': 'Went to hospital to have the baby',
            'Father': 'Told Bobby the baby was a boy',
            'Andy': 'Could not play soccer yet',
        },
    ),

    # 4. Visual Matching (5)
    visual_match('A New Baby', 'Mother', ['Hospital', 'Baby', 'Hand', 'Mother', 'Father']),
    visual_match('A New Baby', 'Father', ['Baby', 'Hand', 'Mother', 'Father', 'Hospital']),
    visual_match('A New Baby', 'Hospital', ['Hand', 'Mother', 'Father', 'Hospital', 'Baby']),
    visual_match('A New Baby', 'Baby', ['Mother', 'Father', 'Hospital', 'Baby', 'Hand']),
    visual_match('A New Baby', 'Hand', ['Father', 'Hospital', 'Baby', 'Hand', 'Mother']),

    # 5. Spelling (5) — Drag Letters (unscramble)
    unscramble('A New Baby', ['M', 'O', 'T', 'H', 'E', 'R'], 'MOTHER'),
    unscramble('A New Baby', ['F', 'A', 'T', 'H', 'E', 'R'], 'FATHER'),
    unscramble('A New Baby', ['H', 'O', 'S', 'P', 'I', 'T', 'A', 'L'], 'HOSPITAL'),
    unscramble('A New Baby', ['B', 'A', 'B', 'Y'], 'BABY'),
    unscramble('A New Baby', ['H', 'A', 'N', 'D'], 'HAND'),

    # 6. Fix the Mistake (5)
    fix_the_mistake(
        'Bobby wanted a big sister, not a baby.',
        ['brother', 'dog', 'friend'],
        'brother',
    ),
    fix_the_mistake(
        'Mother went to school to have the baby.',
        ['hospital', 'home', 'shop'],
        'hospital',
    ),
    fix_the_mistake(
        'Father said, "It is a puppy."',
        ['boy', 'kitten', 'girl'],
        'boy',
    ),
    fix_the_mistake(
        "The baby's name was Thabo.",
        ['Andy', 'Sipho', 'Ben'],
        'Andy',
    ),
    fix_the_mistake(
        'Baby Andy lifted his foot for a high five.',
        ['hand', 'arm', 'head'],
        'hand',
    ),
]


# --- The School Shed Is on Fire ------------------------------------------
THE_SCHOOL_SHED_IS_ON_FIRE_ACTIVITIES = [
    # 1. Comprehension Questions (5)
    comprehension(
        'The class smelled smoke. What did Ben the dog do next?',
        ['Barked and ran away', 'Sniffed the air', 'Went to sleep', 'Hid under a desk'],
        'Sniffed the air',
    ),
    comprehension(
        'Everyone stood safely under the trees. What did the teacher do next?',
        ['Started a lesson', 'Phoned the fire service', 'Went back inside', 'Rang the bell'],
        'Phoned the fire service',
    ),
    comprehension(
        'The firefighters arrived. What did they carry?',
        ['Buckets of sand', 'Masks, belts and equipment', 'Blankets', 'Fans'],
        'Masks, belts and equipment',
    ),
    comprehension(
        'The firefighters sprayed water with the hose. What happened next?',
        ['The shed burned down', 'The fire went out and the shed was saved', 'Everyone went home', 'The bell rang again'],
        'The fire went out and the shed was saved',
    ),
    comprehension(
        'The teacher led the learners outside. Where did they stand?',
        ['Behind the school', 'In a line under the trees', 'Near the fire', 'Inside the hall'],
        'In a line under the trees',
    ),

    # 2. Match It! (4 pairs + 1 decoy)
    match_it(
        ['Ben the dog', 'Teacher', 'Firefighters', 'Hose'],
        [
            'Sniffed the smoke first',
            'Phoned the fire service',
            'Carried masks, belts and equipment',
            'Sprayed water on the flames',
            'Was saved from the fire',  # decoy
        ],
        {
            'Ben the dog': 'Sniffed the smoke first',
            'Teacher': 'Phoned the fire service',
            'Firefighters': 'Carried masks, belts and equipment',
            'Hose': 'Sprayed water on the flames',
        },
    ),

    # 4. Visual Matching (5)
    visual_match('The School Shed Is on Fire', 'Smoke', ['Bell', 'Firefighter', 'Hose', 'Smoke', 'Teacher']),
    visual_match('The School Shed Is on Fire', 'Teacher', ['Firefighter', 'Hose', 'Smoke', 'Teacher', 'Bell']),
    visual_match('The School Shed Is on Fire', 'Bell', ['Hose', 'Smoke', 'Teacher', 'Bell', 'Firefighter']),
    visual_match('The School Shed Is on Fire', 'Firefighter', ['Smoke', 'Teacher', 'Bell', 'Firefighter', 'Hose']),
    visual_match('The School Shed Is on Fire', 'Hose', ['Teacher', 'Bell', 'Firefighter', 'Hose', 'Smoke']),

    # 5. Spelling (5) — Fill Missing Vowel
    fill_vowel('The School Shed Is on Fire', 'sm_ke', 'smoke', ['o', 'a', 'e'], 'o'),
    fill_vowel('The School Shed Is on Fire', 'h_se', 'hose', ['o', 'a', 'u'], 'o'),
    fill_vowel('The School Shed Is on Fire', 'te_cher', 'teacher', ['a', 'e', 'i'], 'a'),
    fill_vowel('The School Shed Is on Fire', 'b_ll', 'bell', ['e', 'a', 'i'], 'e'),
    fill_vowel('The School Shed Is on Fire', 'f_re', 'fire', ['i', 'a', 'e'], 'i'),

    # 6. Fix the Mistake (5)
    fix_the_mistake(
        'The class smelled perfume.',
        ['smoke', 'food', 'flowers'],
        'smoke',
    ),
    fix_the_mistake(
        'The teacher told everyone to stand in a circle under the trees.',
        ['line', 'group', 'row'],
        'line',
    ),
    fix_the_mistake(
        'Two firefighters arrived.',
        ['Six', 'Two', 'Ten'],
        'Six',
    ),
    fix_the_mistake(
        'The firefighters used buckets to put out the fire.',
        ['a hose', 'blankets', 'fans'],
        'a hose',
    ),
    fix_the_mistake(
        'The school was saved.',
        ['shed', 'shop', 'house'],
        'shed',
    ),
]


# --- Dan's Bad Week ------------------------------------------------------
DANS_BAD_WEEK_ACTIVITIES = [
    # 1. Comprehension Questions (5)
    comprehension(
        'Which sentence is true about Monday?',
        ['Dan woke up early and caught the bus.', 'Dan woke up late and missed the bus.', 'Dan stayed home from school.', 'Dan lost his uniform.'],
        'Dan woke up late and missed the bus.',
    ),
    comprehension(
        'Which sentence is true about Tuesday?',
        ['Dan lost his soccer ball.', 'Dan left his school bag on the bus.', 'Dan arrived late for school.', 'Dan wore the wrong uniform.'],
        'Dan left his school bag on the bus.',
    ),
    comprehension(
        'Which sentence is true about Wednesday?',
        ['Dan got on the wrong bus and went to the wrong school.', 'Dan missed the bus again.', 'Dan forgot his bag again.', 'Dan was sick at home.'],
        'Dan got on the wrong bus and went to the wrong school.',
    ),
    comprehension(
        'Which sentence is true about Thursday?',
        ['Dan could not find his uniform and wore his swimming clothes.', 'Dan wore his soccer kit.', 'Dan stayed home sick.', 'Dan lost his bag.'],
        'Dan could not find his uniform and wore his swimming clothes.',
    ),
    comprehension(
        'Which sentence is true about Friday?',
        ['Dan missed school completely.', 'Dan arrived early but was so tired he fell asleep in class.', 'Dan lost his bag again.', 'Dan wore his swimming clothes.'],
        'Dan arrived early but was so tired he fell asleep in class.',
    ),

    # 2. Match It! (4 pairs + 1 decoy)
    match_it(
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday'],
        [
            'Missed the bus',
            'Left his bag on the bus',
            'Went to the wrong school',
            'Wore his swimming clothes',
            'Fell asleep in class',  # decoy
        ],
        {
            'Monday': 'Missed the bus',
            'Tuesday': 'Left his bag on the bus',
            'Wednesday': 'Went to the wrong school',
            'Thursday': 'Wore his swimming clothes',
        },
    ),

    # 4. Visual Matching (5)
    visual_match("Dan's Bad Week", 'Bus', ['School', 'Uniform', 'Cake', 'Bus', 'Bag']),
    visual_match("Dan's Bad Week", 'Bag', ['Uniform', 'Cake', 'Bus', 'Bag', 'School']),
    visual_match("Dan's Bad Week", 'School', ['Cake', 'Bus', 'Bag', 'School', 'Uniform']),
    visual_match("Dan's Bad Week", 'Uniform', ['Bus', 'Bag', 'School', 'Uniform', 'Cake']),
    visual_match("Dan's Bad Week", 'Cake', ['Bag', 'School', 'Uniform', 'Cake', 'Bus']),

    # 5. Spelling (5) — Choose the Correct Spelling
    choose_spelling("Dan's Bad Week", ['buss', 'buhs', 'boos', 'bus'], 'bus'),
    choose_spelling("Dan's Bad Week", ['bagg', 'baag', 'begg', 'bag'], 'bag'),
    choose_spelling("Dan's Bad Week", ['skool', 'schoool', 'scool', 'school'], 'school'),
    choose_spelling("Dan's Bad Week", ['caek', 'kake', 'caik', 'cake'], 'cake'),
    choose_spelling("Dan's Bad Week", ['bal', 'baal', 'bahl', 'ball'], 'ball'),

    # 6. Fix the Mistake (5)
    fix_the_mistake(
        'On Monday, Dan woke up early and missed the bus.',
        ['late', 'early', 'quickly'],
        'late',
    ),
    fix_the_mistake(
        'On Tuesday, Dan left his shoes on the bus.',
        ['bag', 'shoes', 'hat'],
        'bag',
    ),
    fix_the_mistake(
        'On Wednesday, Dan got on the right bus.',
        ['wrong', 'right', 'same'],
        'wrong',
    ),
    fix_the_mistake(
        'On Thursday, Dan wore his soccer clothes to school.',
        ['swimming', 'soccer', 'school'],
        'swimming',
    ),
    fix_the_mistake(
        'On Sunday, Dan fell into a pool at a family party.',
        ['cake', 'pool', 'chair'],
        'cake',
    ),
]


# --- Spring Day Surprise -------------------------------------------------
SPRING_DAY_SURPRISE_ACTIVITIES = [
    # 1. Comprehension Questions (5)
    comprehension(
        "What did the girls see near the birds' nest?",
        ['Butterflies', 'Bees', 'Frogs', 'Flowers'],
        'Butterflies',
    ),
    comprehension(
        'What date was written on the board?',
        ['1 September', '1 April', '1 June', '1 May'],
        '1 September',
    ),
    comprehension(
        'What were the boys carrying?',
        ['Buckets', 'Books', 'Balls', 'Baskets'],
        'Buckets',
    ),
    comprehension(
        'What did the boys do with the water?',
        ['Splashed the girls', 'Drank it', 'Poured it away', 'Hid it'],
        'Splashed the girls',
    ),
    comprehension(
        'What did Katekani forget after school?',
        ['The water game', 'Her homework', 'Her lunch', 'Her bag'],
        'The water game',
    ),

    # 2. Match It! (4 pairs + 1 decoy)
    match_it(
        ['Morning', 'At school', 'After school', 'Near home'],
        [
            'Saw butterflies and a nest',
            'Teacher announced Spring Day',
            'The girls played and forgot the game',
            'Heard giggling',
            'The boys splashed the girls with water',  # decoy
        ],
        {
            'Morning': 'Saw butterflies and a nest',
            'At school': 'Teacher announced Spring Day',
            'After school': 'The girls played and forgot the game',
            'Near home': 'Heard giggling',
        },
    ),

    # 4. Visual Matching (5)
    visual_match('Spring Day Surprise', 'Butterfly', ['Ball', 'Bucket', 'Water', 'Butterfly', 'Teacher']),
    visual_match('Spring Day Surprise', 'Teacher', ['Bucket', 'Water', 'Butterfly', 'Teacher', 'Ball']),
    visual_match('Spring Day Surprise', 'Ball', ['Water', 'Butterfly', 'Teacher', 'Ball', 'Bucket']),
    visual_match('Spring Day Surprise', 'Bucket', ['Butterfly', 'Teacher', 'Ball', 'Bucket', 'Water']),
    visual_match('Spring Day Surprise', 'Water', ['Teacher', 'Ball', 'Bucket', 'Water', 'Butterfly']),

    # 5. Spelling (5) — Drag Letters (unscramble)
    unscramble('Spring Day Surprise', ['B', 'U', 'T', 'T', 'E', 'R', 'F', 'L', 'Y'], 'BUTTERFLY'),
    unscramble('Spring Day Surprise', ['T', 'E', 'A', 'C', 'H', 'E', 'R'], 'TEACHER'),
    unscramble('Spring Day Surprise', ['B', 'U', 'C', 'K', 'E', 'T'], 'BUCKET'),
    unscramble('Spring Day Surprise', ['W', 'A', 'T', 'E', 'R'], 'WATER'),
    unscramble('Spring Day Surprise', ['B', 'A', 'L', 'L'], 'BALL'),

    # 6. Fix the Mistake (5)
    fix_the_mistake(
        "The girls saw elephants near the birds' nest.",
        ['butterflies', 'elephants', 'lions'],
        'butterflies',
    ),
    fix_the_mistake(
        'The teacher wrote 1 December on the board.',
        ['September', 'December', 'June'],
        'September',
    ),
    fix_the_mistake(
        'The boys were holding books.',
        ['buckets', 'books', 'balls'],
        'buckets',
    ),
    fix_the_mistake(
        'The boys splashed the girls with sand.',
        ['water', 'sand', 'mud'],
        'water',
    ),
    fix_the_mistake(
        'Everyone cried in the warm spring sunshine.',
        ['laughed', 'cried', 'shouted'],
        'laughed',
    ),
]


# The full Grade 2 workbook, keyed by the lesson title in the database.
GRADE_TWO_ACTIVITY_BLUEPRINTS = {
    "A Dog's Life": A_DOGS_LIFE_ACTIVITIES,
    'A New Baby': A_NEW_BABY_ACTIVITIES,
    'The School Shed Is on Fire': THE_SCHOOL_SHED_IS_ON_FIRE_ACTIVITIES,
    "Dan's Bad Week": DANS_BAD_WEEK_ACTIVITIES,
    'Spring Day Surprise': SPRING_DAY_SURPRISE_ACTIVITIES,
}


# The five groups, in the order the document lists them.
ACTIVITY_GROUPS = [
    (1, 'Comprehension Questions'),
    (2, 'Match It!'),
    (3, 'Visual Matching'),
    (4, 'Spelling'),
    (5, 'Fix the Mistake'),
]
