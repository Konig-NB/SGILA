import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from api.models import (
    Lesson, ReadingActivity, ComprehensionQuestion, 
    SequencingActivity, SpellingActivity, VisualActivityItem,
    PronunciationWord
)

# ============================================================
# Data from curriculum_enrichment.py for Grade 2 lessons
# ============================================================

VISUAL_VOCAB_SHEETS = {
    "A Dog's Life": 'g2_dog_vocab.png',
    'A New Baby': 'g2_baby_vocab.png',
    'The School Shed Is on Fire': 'g2_fire_vocab.png',
    "Dan's Bad Week": 'g2_dan_vocab.png',
    'Spring Day Surprise': 'g2_spring_vocab.png',
}

LESSON_WORDS = {
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
}

# Spelling activities from the document
SPELLING_ACTIVITIES = {
    "A Dog's Life": [
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'b_s', 'answer': 'bus'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'b_ok', 'answer': 'book'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'tr_e', 'answer': 'tree'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'cl_ud', 'answer': 'cloud'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'w_ve', 'answer': 'wave'},
    ],
    'A New Baby': [
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'M,O,T,H,E,R', 'answer': 'MOTHER'},
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'F,A,T,H,E,R', 'answer': 'FATHER'},
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'H,O,S,P,I,T,A,L', 'answer': 'HOSPITAL'},
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'B,A,B,Y', 'answer': 'BABY'},
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'H,A,N,D', 'answer': 'HAND'},
    ],
    'The School Shed Is on Fire': [
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'sm_ke', 'answer': 'smoke'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'h_se', 'answer': 'hose'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'te_cher', 'answer': 'teacher'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'b_ll', 'answer': 'bell'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'f_re', 'answer': 'fire'},
    ],
    "Dan's Bad Week": [
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? buss / buhs / boos / bus', 'answer': 'bus'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? bagg / baag / begg / bag', 'answer': 'bag'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? skool / schoool / scool / school', 'answer': 'school'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? caek / kake / caik / cake', 'answer': 'cake'},
        {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? bal / baal / bahl / ball', 'answer': 'ball'},
    ],
    'Spring Day Surprise': [
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'B,U,T,T,E,R,F,L,Y', 'answer': 'BUTTERFLY'},
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'T,E,A,C,H,E,R', 'answer': 'TEACHER'},
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'B,U,C,K,E,T', 'answer': 'BUCKET'},
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'W,A,T,E,R', 'answer': 'WATER'},
        {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'B,A,L,L', 'answer': 'BALL'},
    ],
}

# Comprehension questions from the document
COMPREHENSION_QUESTIONS = {
    "A Dog's Life": [
        {
            'question': "Why couldn't Ben get on the school bus?",
            'option_1': "He was too big",
            'option_2': "No dogs allowed",
            'option_3': "He was scared",
            'option_4': "He was sick",
            'correct_answer': "No dogs allowed",
        },
        {
            'question': "Where did Ben wait while Abby and Lebo were at the park?",
            'option_1': "In the classroom",
            'option_2': "On the bus",
            'option_3': "Under a tree at the gate",
            'option_4': "At the beach",
            'correct_answer': "Under a tree at the gate",
        },
        {
            'question': "What did Ben dream about doing at school?",
            'option_1': "Riding the bus and sitting in class",
            'option_2': "Cooking dinner",
            'option_3': "Driving a car",
            'option_4': "Reading a book",
            'correct_answer': "Riding the bus and sitting in class",
        },
        {
            'question': "What did Ben dream about doing at the beach?",
            'option_1': "Digging in the sand and surfing in the waves",
            'option_2': "Fishing all day",
            'option_3': "Building a sandcastle only",
            'option_4': "Sleeping under an umbrella",
            'correct_answer': "Digging in the sand and surfing in the waves",
        },
        {
            'question': "What happened when Abby and Lebo came back?",
            'option_1': "Ben ran away",
            'option_2': "Ben woke up and realised it was a dream",
            'option_3': "Ben got on the bus",
            'option_4': "Ben cried",
            'correct_answer': "Ben woke up and realised it was a dream",
        },
    ],
    'A New Baby': [
        {
            'question': '"Is it a girl or a boy?" - Who asked this?',
            'option_1': "Bobby",
            'option_2': "Father",
            'option_3': "Granny",
            'option_4': "Mother",
            'correct_answer': "Bobby",
        },
        {
            'question': '"It is a boy." - Who said this?',
            'option_1': "Bobby",
            'option_2': "Father",
            'option_3': "Mother",
            'option_4': "Granny",
            'correct_answer': "Father",
        },
        {
            'question': '"He is so cute. He looks just like me." - Who said this?',
            'option_1': "Granny",
            'option_2': "Father",
            'option_3': "Bobby",
            'option_4': "Mother",
            'correct_answer': "Bobby",
        },
        {
            'question': '"I love you just as you are." - Who said this to baby Andy?',
            'option_1': "Mother",
            'option_2': "Father",
            'option_3': "Bobby",
            'option_4': "Granny",
            'correct_answer': "Bobby",
        },
        {
            'question': '"Granny would look after him while she was in hospital." - Who said this to Bobby?',
            'option_1': "Mother",
            'option_2': "Father",
            'option_3': "Granny",
            'option_4': "Andy",
            'correct_answer': "Mother",
        },
    ],
    'The School Shed Is on Fire': [
        {
            'question': "The class smelled smoke. What did Ben the dog do next?",
            'option_1': "Barked and ran away",
            'option_2': "Sniffed the air",
            'option_3': "Went to sleep",
            'option_4': "Hid under a desk",
            'correct_answer': "Sniffed the air",
        },
        {
            'question': "Everyone stood safely under the trees. What did the teacher do next?",
            'option_1': "Started a lesson",
            'option_2': "Phoned the fire service",
            'option_3': "Went back inside",
            'option_4': "Rang the bell",
            'correct_answer': "Phoned the fire service",
        },
        {
            'question': "The firefighters arrived. What did they carry?",
            'option_1': "Buckets of sand",
            'option_2': "Masks, belts and equipment",
            'option_3': "Blankets",
            'option_4': "Fans",
            'correct_answer': "Masks, belts and equipment",
        },
        {
            'question': "The firefighters sprayed water with the hose. What happened next?",
            'option_1': "The shed burned down",
            'option_2': "The fire went out and the shed was saved",
            'option_3': "Everyone went home",
            'option_4': "The bell rang again",
            'correct_answer': "The fire went out and the shed was saved",
        },
        {
            'question': "The teacher led the learners outside. Where did they stand?",
            'option_1': "Behind the school",
            'option_2': "In a line under the trees",
            'option_3': "Near the fire",
            'option_4': "Inside the hall",
            'correct_answer': "In a line under the trees",
        },
    ],
    "Dan's Bad Week": [
        {
            'question': "Which sentence is true about Monday?",
            'option_1': "Dan woke up early and caught the bus.",
            'option_2': "Dan woke up late and missed the bus.",
            'option_3': "Dan stayed home from school.",
            'option_4': "Dan lost his uniform.",
            'correct_answer': "Dan woke up late and missed the bus.",
        },
        {
            'question': "Which sentence is true about Tuesday?",
            'option_1': "Dan lost his soccer ball.",
            'option_2': "Dan left his school bag on the bus.",
            'option_3': "Dan arrived late for school.",
            'option_4': "Dan wore the wrong uniform.",
            'correct_answer': "Dan left his school bag on the bus.",
        },
        {
            'question': "Which sentence is true about Wednesday?",
            'option_1': "Dan got on the wrong bus and went to the wrong school.",
            'option_2': "Dan missed the bus again.",
            'option_3': "Dan forgot his bag again.",
            'option_4': "Dan was sick at home.",
            'correct_answer': "Dan got on the wrong bus and went to the wrong school.",
        },
        {
            'question': "Which sentence is true about Thursday?",
            'option_1': "Dan could not find his uniform and wore his swimming clothes.",
            'option_2': "Dan wore his soccer kit.",
            'option_3': "Dan stayed home sick.",
            'option_4': "Dan lost his bag.",
            'correct_answer': "Dan could not find his uniform and wore his swimming clothes.",
        },
        {
            'question': "Which sentence is true about Friday?",
            'option_1': "Dan missed school completely.",
            'option_2': "Dan arrived early but was so tired he fell asleep in class.",
            'option_3': "Dan lost his bag again.",
            'option_4': "Dan wore his swimming clothes.",
            'correct_answer': "Dan arrived early but was so tired he fell asleep in class.",
        },
    ],
    'Spring Day Surprise': [
        {
            'question': "What did the girls see near the birds' nest?",
            'option_1': "Butterflies",
            'option_2': "Bees",
            'option_3': "Frogs",
            'option_4': "Flowers",
            'correct_answer': "Butterflies",
        },
        {
            'question': "What date was written on the board?",
            'option_1': "1 September",
            'option_2': "1 April",
            'option_3': "1 June",
            'option_4': "1 May",
            'correct_answer': "1 September",
        },
        {
            'question': "What were the boys carrying?",
            'option_1': "Buckets",
            'option_2': "Books",
            'option_3': "Balls",
            'option_4': "Baskets",
            'correct_answer': "Buckets",
        },
        {
            'question': "What did the boys do with the water?",
            'option_1': "Splashed the girls",
            'option_2': "Drank it",
            'option_3': "Poured it away",
            'option_4': "Hid it",
            'correct_answer': "Splashed the girls",
        },
        {
            'question': "What did Katekani forget after school?",
            'option_1': "The water game",
            'option_2': "Her homework",
            'option_3': "Her lunch",
            'option_4': "Her bag",
            'correct_answer': "The water game",
        },
    ],
}

# Match It! activities from the document
MATCH_IT_ACTIVITIES = {
    "A Dog's Life": {
        'question': "Match each place to what happened there.",
        'left_items': ['Bus', 'Beach', 'Park', 'Dream'],
        'right_items': ['No dogs allowed', 'Ben could not go with them', 'Ben waited under a tree', 'Ben surfed in the waves', 'Ben could not go inside'],
        'correct_pairs': {
            'Bus': 'No dogs allowed',
            'Beach': 'Ben could not go with them',
            'Park': 'Ben waited under a tree',
            'Dream': 'Ben surfed in the waves',
        }
    },
    'A New Baby': {
        'question': "Match each person to what they did.",
        'left_items': ['Bobby', 'Mother', 'Father', 'Andy'],
        'right_items': ['Wanted a big brother, not a baby', 'Went to hospital to have the baby', 'Told Bobby the baby was a boy', 'Could not play soccer yet', 'Looked after Bobby while Mother was away'],
        'correct_pairs': {
            'Bobby': 'Wanted a big brother, not a baby',
            'Mother': 'Went to hospital to have the baby',
            'Father': 'Told Bobby the baby was a boy',
            'Andy': 'Could not play soccer yet',
        }
    },
    'The School Shed Is on Fire': {
        'question': "Match each person/thing to what they did.",
        'left_items': ['Ben the dog', 'Teacher', 'Firefighters', 'Hose'],
        'right_items': ['Sniffed the smoke first', 'Phoned the fire service', 'Carried masks, belts and equipment', 'Sprayed water on the flames', 'Was saved from the fire'],
        'correct_pairs': {
            'Ben the dog': 'Sniffed the smoke first',
            'Teacher': 'Phoned the fire service',
            'Firefighters': 'Carried masks, belts and equipment',
            'Hose': 'Sprayed water on the flames',
        }
    },
    "Dan's Bad Week": {
        'question': "Match each day to what happened.",
        'left_items': ['Monday', 'Tuesday', 'Wednesday', 'Thursday'],
        'right_items': ['Missed the bus', 'Left his bag on the bus', 'Went to the wrong school', 'Wore his swimming clothes', 'Fell asleep in class'],
        'correct_pairs': {
            'Monday': 'Missed the bus',
            'Tuesday': 'Left his bag on the bus',
            'Wednesday': 'Went to the wrong school',
            'Thursday': 'Wore his swimming clothes',
        }
    },
    'Spring Day Surprise': {
        'question': "Match each time to what happened.",
        'left_items': ['Morning', 'At school', 'After school', 'Near home'],
        'right_items': ['Saw butterflies and a nest', 'Teacher announced Spring Day', 'The girls played and forgot the game', 'Heard giggling', 'The boys splashed the girls with water'],
        'correct_pairs': {
            'Morning': 'Saw butterflies and a nest',
            'At school': 'Teacher announced Spring Day',
            'After school': 'The girls played and forgot the game',
            'Near home': 'Heard giggling',
        }
    },
}

# Story Sequencer activities from the document
SEQUENCER_ACTIVITIES = {
    "A Dog's Life": {
        'instruction': "Put these events in the correct order.",
        'ordered_events': [
            "Ben is not allowed on the bus",
            "Ben is not allowed at the library or beach",
            "Ben waits under the tree at the park",
            "Ben falls asleep and dreams of an adventure",
            "Abby and Lebo wake Ben up"
        ]
    },
    'A New Baby': {
        'instruction': "Put these events in order.",
        'ordered_events': [
            "Mother tells Bobby about the baby",
            "Mother goes to hospital",
            "Father tells Bobby the baby is born",
            "Bobby visits the hospital and meets Andy",
            "Andy lifts his hand for a high five"
        ]
    },
    'The School Shed Is on Fire': {
        'instruction': "Put these events in the correct order.",
        'ordered_events': [
            "The class smells smoke",
            "Everyone stands in a line under the trees",
            "The teacher phones the fire service",
            "Firefighters arrive with equipment",
            "The fire is put out and the shed is saved"
        ]
    },
    "Dan's Bad Week": {
        'instruction': "Put these events in order from Monday to Friday.",
        'ordered_events': [
            "Monday: Dan misses the bus",
            "Tuesday: Dan leaves his bag on the bus",
            "Wednesday: Dan goes to the wrong school",
            "Thursday: Dan wears his swimming clothes",
            "Friday: Dan falls asleep in class"
        ]
    },
    'Spring Day Surprise': {
        'instruction': "Put these events in order.",
        'ordered_events': [
            "Morning: the girls walk to school and see butterflies",
            "At school: the teacher announces Spring Day",
            "After school: the girls play outside",
            "Katekani remembers the water game and hurries home",
            "Near home: the boys splash the girls with water"
        ]
    },
}

# Fix the Mistake activities from the document
FIX_MISTAKE_ACTIVITIES = {
    "A Dog's Life": [
        {
            'question': "Ben could not get onto the car.",
            'options': ['bus', 'van', 'truck'],
            'correct_answer': 'bus',
        },
        {
            'question': "On Friday, Abby and Lebo went to the beach, but Ben could not go inside.",
            'options': ['library', 'park', 'shop'],
            'correct_answer': 'library',
        },
        {
            'question': "Ben sat under a table at the gate.",
            'options': ['tree', 'bench', 'wall'],
            'correct_answer': 'tree',
        },
        {
            'question': "In his dream, Ben rode the car and sat at the front.",
            'options': ['bus', 'taxi', 'train'],
            'correct_answer': 'bus',
        },
        {
            'question': "Ben opened his eyes and realised his adventure had been a story.",
            'options': ['dream', 'game', 'trick'],
            'correct_answer': 'dream',
        },
    ],
    'A New Baby': [
        {
            'question': "Bobby wanted a big sister, not a baby.",
            'options': ['brother', 'dog', 'friend'],
            'correct_answer': 'brother',
        },
        {
            'question': "Mother went to school to have the baby.",
            'options': ['hospital', 'home', 'shop'],
            'correct_answer': 'hospital',
        },
        {
            'question': 'Father said, "It is a puppy."',
            'options': ['boy', 'kitten', 'girl'],
            'correct_answer': 'boy',
        },
        {
            'question': "The baby's name was Thabo.",
            'options': ['Andy', 'Sipho', 'Ben'],
            'correct_answer': 'Andy',
        },
        {
            'question': "Baby Andy lifted his foot for a high five.",
            'options': ['hand', 'arm', 'head'],
            'correct_answer': 'hand',
        },
    ],
    'The School Shed Is on Fire': [
        {
            'question': "The class smelled perfume.",
            'options': ['smoke', 'food', 'flowers'],
            'correct_answer': 'smoke',
        },
        {
            'question': "The teacher told everyone to stand in a circle under the trees.",
            'options': ['line', 'group', 'row'],
            'correct_answer': 'line',
        },
        {
            'question': "Two firefighters arrived.",
            'options': ['Six', 'Two', 'Ten'],
            'correct_answer': 'Six',
        },
        {
            'question': "The firefighters used buckets to put out the fire.",
            'options': ['a hose', 'blankets', 'fans'],
            'correct_answer': 'a hose',
        },
        {
            'question': "The school was saved.",
            'options': ['shed', 'shop', 'house'],
            'correct_answer': 'shed',
        },
    ],
    "Dan's Bad Week": [
        {
            'question': "On Monday, Dan woke up early and missed the bus.",
            'options': ['late', 'early', 'quickly'],
            'correct_answer': 'late',
        },
        {
            'question': "On Tuesday, Dan left his shoes on the bus.",
            'options': ['bag', 'shoes', 'hat'],
            'correct_answer': 'bag',
        },
        {
            'question': "On Wednesday, Dan got on the right bus.",
            'options': ['wrong', 'right', 'same'],
            'correct_answer': 'wrong',
        },
        {
            'question': "On Thursday, Dan wore his soccer clothes to school.",
            'options': ['swimming', 'soccer', 'school'],
            'correct_answer': 'swimming',
        },
        {
            'question': "On Sunday, Dan fell into a pool at a family party.",
            'options': ['cake', 'pool', 'chair'],
            'correct_answer': 'cake',
        },
    ],
    'Spring Day Surprise': [
        {
            'question': "The girls saw elephants near the birds' nest.",
            'options': ['butterflies', 'elephants', 'lions'],
            'correct_answer': 'butterflies',
        },
        {
            'question': "The teacher wrote 1 December on the board.",
            'options': ['September', 'December', 'June'],
            'correct_answer': 'September',
        },
        {
            'question': "The boys were holding books.",
            'options': ['buckets', 'books', 'balls'],
            'correct_answer': 'buckets',
        },
        {
            'question': "The boys splashed the girls with sand.",
            'options': ['water', 'sand', 'mud'],
            'correct_answer': 'water',
        },
        {
            'question': "Everyone cried in the warm spring sunshine.",
            'options': ['laughed', 'cried', 'shouted'],
            'correct_answer': 'laughed',
        },
    ],
}

# ============================================================
# Helper functions
# ============================================================

import random

def create_visual_items(lesson):
    """Create visual matching items using vocab sheet panels"""
    lesson_words = LESSON_WORDS.get(lesson.title)
    vocab_sheet = VISUAL_VOCAB_SHEETS.get(lesson.title)
    
    if not lesson_words or not vocab_sheet:
        print(f"  WARNING: No lesson words or vocab sheet for {lesson.title}")
        return
    
    lesson.visual_items.all().delete()
    
    english_words = [word for word, _isizulu, _image in lesson_words]
    
    for word, isizulu_word, image_source in lesson_words:
        image_url = f'/static/img/vocab_sheets/{vocab_sheet}#panel-{image_source}'
        options = english_words.copy()
        random.Random(f'{lesson.title}:{word}').shuffle(options)
        VisualActivityItem.objects.create(
            lesson=lesson,
            image_url=image_url,
            correct_word=word,
            word_options=','.join(options),
        )
    print(f"  Created {len(lesson_words)} visual matching items for {lesson.title}")

def create_pronunciation_words(lesson):
    """Create pronunciation words using vocab sheet panels"""
    lesson_words = LESSON_WORDS.get(lesson.title)
    vocab_sheet = VISUAL_VOCAB_SHEETS.get(lesson.title)
    
    if not lesson_words or not vocab_sheet:
        return
    
    lesson.pronunciation_words.all().delete()
    
    for word, isizulu_word, image_source in lesson_words:
        image_url = f'/static/img/vocab_sheets/{vocab_sheet}#panel-{image_source}'
        audio_slug = word.lower().replace(' ', '-')
        PronunciationWord.objects.create(
            lesson=lesson,
            word=word,
            image_url=image_url,
            english_audio=f'voiceover:{audio_slug}-english',
            isizulu_audio=f'voiceover:{audio_slug}-zulu',
            isizulu_word=isizulu_word,
        )
    print(f"  Created {len(lesson_words)} pronunciation words for {lesson.title}")

def create_spelling_activities(lesson):
    """Create spelling activities"""
    spelling_data = SPELLING_ACTIVITIES.get(lesson.title, [])
    lesson.spelling_activities.all().delete()
    
    for s in spelling_data:
        SpellingActivity.objects.create(lesson=lesson, **s)
    print(f"  Created {len(spelling_data)} spelling activities for {lesson.title}")

def create_comprehension_questions(lesson):
    """Create comprehension questions"""
    questions = COMPREHENSION_QUESTIONS.get(lesson.title, [])
    lesson.questions.all().delete()
    
    for q in questions:
        ComprehensionQuestion.objects.create(lesson=lesson, **q)
    print(f"  Created {len(questions)} comprehension questions for {lesson.title}")

def create_reading_activities(lesson):
    """Create reading activities (Match It! and Fix the Mistake)"""
    lesson.reading_activities.all().delete()
    
    # Match It! activity
    match_it = MATCH_IT_ACTIVITIES.get(lesson.title)
    if match_it:
        # Build options dict with shuffled right items for each left item
        right_items = match_it['right_items']
        options = {}
        for left in match_it['left_items']:
            shuffled = right_items.copy()
            random.Random(f'{lesson.title}:match:{left}').shuffle(shuffled)
            options[left] = shuffled
        
        # Build correct answer string
        correct_pairs = match_it['correct_pairs']
        correct_answer = '; '.join([f"{k}: {v}" for k, v in correct_pairs.items()])
        
        ReadingActivity.objects.create(
            lesson=lesson,
            activity_type=ReadingActivity.MATCHING,
            skill='literal_comprehension',
            question=match_it['question'],
            options=options,
            correct_answer=correct_answer,
            order=1,
            group_number=1,
            group_title="Match It!",
        )
    
    # Fix the Mistake activities
    fix_mistakes = FIX_MISTAKE_ACTIVITIES.get(lesson.title, [])
    for i, fm in enumerate(fix_mistakes, 1):
        ReadingActivity.objects.create(
            lesson=lesson,
            activity_type=ReadingActivity.CLOZE,
            skill='literal_comprehension',
            question=fm['question'],
            options=fm['options'],
            correct_answer=fm['correct_answer'],
            order=i,
            group_number=2,
            group_title="Fix the Mistake",
        )
    
    total_activities = 1 + len(fix_mistakes) if match_it else len(fix_mistakes)
    print(f"  Created {total_activities} reading activities for {lesson.title}")

def create_sequencing_activity(lesson):
    """Create story sequencer activity"""
    lesson.sequencing_activities.all().delete()
    
    seq = SEQUENCER_ACTIVITIES.get(lesson.title)
    if seq:
        SequencingActivity.objects.create(
            lesson=lesson,
            instruction=seq['instruction'],
            ordered_events='|'.join(seq['ordered_events']),
        )
        print(f"  Created story sequencer for {lesson.title}")

# ============================================================
# Process all Grade 2 lessons
# ============================================================

grade2_lessons = Lesson.objects.filter(grade=2).order_by('id')

for lesson in grade2_lessons:
    print(f"\n=== Processing {lesson.title} ===")
    
    create_comprehension_questions(lesson)
    create_reading_activities(lesson)
    create_sequencing_activity(lesson)
    create_visual_items(lesson)
    create_pronunciation_words(lesson)
    create_spelling_activities(lesson)

print("\n=== All Grade 2 lessons updated ===")