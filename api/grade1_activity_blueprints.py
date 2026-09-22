"""The canonical three-by-three activity structure for every Grade 1 story."""


HOT_STORYBOARD = '/static/img/storyboards/g1_hot_storyboard.png'
HOT_VOCAB = '/static/img/vocab_sheets/g1_hot_vocab.png'
BEN_STORYBOARD = '/static/img/storyboards/g1_ben_storyboard.png'
BEN_VOCAB = '/static/img/vocab_sheets/g1_ben_vocab.png'
OLWETHU_STORYBOARD = '/static/img/storyboards/g1_olwethu_storyboard.png'
OLWETHU_VOCAB = '/static/img/vocab_sheets/g1_olwethu_vocab.png'
BONGI_STORYBOARD = '/static/img/storyboards/g1_bongi_storyboard.png'
BONGI_VOCAB = '/static/img/vocab_sheets/g1_bongi_vocab.png'


def _panel(sheet, number):
    return f'{sheet}#panel-{number}'


def _phonics(display_word, word, choices, answer, image):
    return {
        'activity_type': 'cloze',
        'skill': 'spelling',
        'question': f'Complete the word: {display_word}',
        'options': {
            'presentation': 'grade1_phonics',
            'choices': choices,
            'audio_text': word,
            'display_word': display_word,
            'prompt_image': image,
            'prompt_alt': word,
            'instruction': 'Listen to the word and choose the missing letter.',
        },
        'correct_answer': answer,
        'group_number': 1,
        'group_title': 'Phonics & Story-Word Spelling',
    }


def _picture(image, alt):
    return {'image_url': image, 'alt': alt}


def _picture_match(sentence, pictures, correct_picture):
    choices = [
        {
            **picture,
            'value': f'Picture {index}',
            'label': f'Picture {index}',
        }
        for index, picture in enumerate(pictures, start=1)
    ]
    return {
        'activity_type': 'multiple_choice',
        'skill': 'literal_comprehension',
        'question': sentence,
        'options': {
            'presentation': 'visual_choice',
            'choices': choices,
            'audio_text': sentence,
            'instruction': 'Listen to or read the sentence, then choose the matching picture.',
        },
        'correct_answer': f'Picture {correct_picture}',
        'group_number': 2,
        'group_title': 'Short Sentences & Picture Matching',
    }


def _sentence_completion(question, choices, answer, image, alt):
    return {
        'activity_type': 'multiple_choice',
        'skill': 'vocabulary_in_context',
        'question': question,
        'options': {
            'choices': choices,
            'audio_text': question,
            'prompt_image': image,
            'prompt_alt': alt,
            'instruction': 'Listen to the sentence, then choose the missing word.',
        },
        'correct_answer': answer,
        'group_number': 3,
        'group_title': 'Story Sentence Completion',
    }


LERATO_BASKET = '/static/img/lerato/lerato_basket.png'
LERATO_MARKET = '/static/img/lerato/lerato_market.png'
LERATO_EATING = '/static/img/lerato/lerato_eating.png'
LERATO_APPLE = '/static/img/lerato/fruit_apple.png'
LERATO_BANANA = '/static/img/lerato/fruit_banana.png'
LERATO_MANGO = '/static/img/lerato/fruit_mango_user.webp'

LERATOS_FRUIT_BASKET_ACTIVITIES = [
    _phonics('A P P _ E', 'apple', ['L', 'T', 'N'], 'L', LERATO_APPLE),
    _phonics('B A _ A N A', 'banana', ['T', 'N', 'M'], 'N', LERATO_BANANA),
    _phonics('M A N _ O', 'mango', ['T', 'L', 'G'], 'G', LERATO_MANGO),
    _picture_match('Lerato has a basket of fruit at home.', [
        _picture(LERATO_MARKET, 'Mother buying fruit at the market.'),
        _picture(LERATO_BASKET, 'Lerato with her fruit basket.'),
        _picture(LERATO_EATING, 'Lerato eating fruit.'),
    ], 2),
    _picture_match('Mother bought a mango at the market.', [
        _picture(LERATO_EATING, 'Lerato eating fruit.'),
        _picture(LERATO_BASKET, 'Lerato with her fruit basket.'),
        _picture(LERATO_MARKET, 'Mother buying fruit at the market.'),
    ], 3),
    _picture_match('Lerato eats fruit to stay healthy and strong.', [
        _picture(LERATO_EATING, 'Lerato eating fruit.'),
        _picture(LERATO_MARKET, 'Mother buying fruit at the market.'),
        _picture(LERATO_BASKET, 'Lerato with her fruit basket.'),
    ], 1),
    _sentence_completion('The apple is ..........', ['Red', 'Green'], 'Red', LERATO_APPLE, 'A red apple'),
    _sentence_completion('The banana is ..........', ['Yellow', 'Blue'], 'Yellow', LERATO_BANANA, 'A yellow banana'),
    _sentence_completion('Lerato wants to be ..........', ['Strong', 'Weak'], 'Strong', LERATO_EATING, 'Lerato eating healthy fruit'),
]


HOT_SOCCER = _panel(HOT_STORYBOARD, 1)
HOT_POND = _panel(HOT_STORYBOARD, 3)
HOT_WATER = _panel(HOT_STORYBOARD, 5)
HOT_FISH = _panel(HOT_STORYBOARD, 6)

A_VERY_HOT_DAY_ACTIVITIES = [
    _phonics('H O _', 'hot', ['P', 'T', 'S'], 'T', HOT_SOCCER),
    _phonics('P _ N D', 'pond', ['A', 'E', 'O'], 'O', _panel(HOT_VOCAB, 3)),
    _phonics('F _ S H', 'fish', ['I', 'A', 'O'], 'I', _panel(HOT_VOCAB, 5)),
    _picture_match('The friends played soccer.', [
        _picture(HOT_POND, 'Karabo remembers the pond.'),
        _picture(HOT_SOCCER, 'The friends play soccer.'),
        _picture(HOT_WATER, 'Karabo jumps into the water.'),
    ], 2),
    _picture_match('Karabo remembered the pond.', [
        _picture(HOT_SOCCER, 'The friends play soccer.'),
        _picture(HOT_WATER, 'Karabo jumps into the water.'),
        _picture(HOT_POND, 'Karabo remembers the pond.'),
    ], 3),
    _picture_match('Karabo jumped into the water.', [
        _picture(HOT_WATER, 'Karabo jumps into the water.'),
        _picture(HOT_FISH, 'A fish rests on Karabo\'s head.'),
        _picture(HOT_POND, 'Karabo remembers the pond.'),
    ], 1),
    _sentence_completion('The day is ..........', ['Hot', 'Cold'], 'Hot', HOT_SOCCER, 'A very hot day'),
    _sentence_completion('Karabo jumps into the ..........', ['Pond', 'School'], 'Pond', HOT_WATER, 'Karabo jumping into the pond'),
    _sentence_completion('Karabo is .......... with Cathy.', ['Happy', 'Sad'], 'Happy', HOT_FISH, 'Karabo and Cathy laughing'),
]


BEN_SCHOOL = _panel(BEN_VOCAB, 1)
BEN_BAG = _panel(BEN_VOCAB, 3)
BEN_BALL = _panel(BEN_VOCAB, 5)
BEN_WALK = _panel(BEN_STORYBOARD, 1)
BEN_CLASSROOM = _panel(BEN_STORYBOARD, 3)
BEN_CHASES = _panel(BEN_STORYBOARD, 5)
BEN_ENDING = _panel(BEN_STORYBOARD, 6)

BEN_GOES_TO_SCHOOL_ACTIVITIES = [
    _phonics('S C H _ O L', 'school', ['O', 'A', 'E'], 'O', BEN_SCHOOL),
    _phonics('B _ G', 'bag', ['E', 'O', 'A'], 'A', BEN_BAG),
    _phonics('B _ L L', 'ball', ['O', 'A', 'E'], 'A', BEN_BALL),
    _picture_match('Jabu walked to school.', [
        _picture(BEN_CLASSROOM, 'The class sings together.'),
        _picture(BEN_WALK, 'Jabu walks to school.'),
        _picture(BEN_CHASES, 'Ben chases the ball.'),
    ], 2),
    _picture_match('The class sang a song.', [
        _picture(BEN_WALK, 'Jabu walks to school.'),
        _picture(BEN_CHASES, 'Ben chases the ball.'),
        _picture(BEN_CLASSROOM, 'The class sings together.'),
    ], 3),
    _picture_match('Ben chased the ball at break.', [
        _picture(BEN_CHASES, 'Ben chases the ball.'),
        _picture(BEN_CLASSROOM, 'The class sings together.'),
        _picture(BEN_WALK, 'Jabu walks to school.'),
    ], 1),
    _sentence_completion('Ben goes to ..........', ['School', 'Home'], 'School', BEN_WALK, 'Ben going to school'),
    _sentence_completion('The children are .......... together.', ['Singing', 'Sleeping'], 'Singing', BEN_CLASSROOM, 'The children singing together'),
    _sentence_completion('Jabu is .......... to see Ben.', ['Happy', 'Sad'], 'Happy', BEN_ENDING, 'Jabu happy to see Ben'),
]


OLWETHU_GOING_TO_SCHOOL = _panel(OLWETHU_STORYBOARD, 1)
OLWETHU_GETS_READY = _panel(OLWETHU_STORYBOARD, 2)
OLWETHU_WANTS_HOME = _panel(OLWETHU_STORYBOARD, 3)
OLWETHU_MAKES_FRIEND = _panel(OLWETHU_STORYBOARD, 6)

OLWETHUS_FIRST_DAY_ACTIVITIES = [
    _phonics('S C _ O O L', 'school', ['B', 'H', 'T'], 'H', _panel(OLWETHU_VOCAB, 3)),
    _phonics('S H _ E S', 'shoes', ['O', 'A', 'E'], 'O', OLWETHU_GETS_READY),
    _phonics('F _ I E N D', 'friend', ['L', 'N', 'R'], 'R', _panel(OLWETHU_VOCAB, 4)),
    _picture_match('Olwethu was going to school.', [
        _picture(OLWETHU_GETS_READY, 'Olwethu gets ready.'),
        _picture(OLWETHU_GOING_TO_SCHOOL, 'Olwethu goes to school.'),
        _picture(OLWETHU_MAKES_FRIEND, 'Olwethu makes a friend.'),
    ], 2),
    _picture_match('Gogo and Mother helped Olwethu.', [
        _picture(OLWETHU_GOING_TO_SCHOOL, 'Olwethu goes to school.'),
        _picture(OLWETHU_MAKES_FRIEND, 'Olwethu makes a friend.'),
        _picture(OLWETHU_GETS_READY, 'Olwethu gets ready.'),
    ], 3),
    _picture_match('Olwethu made a friend.', [
        _picture(OLWETHU_MAKES_FRIEND, 'Olwethu makes a friend.'),
        _picture(OLWETHU_GETS_READY, 'Olwethu gets ready.'),
        _picture(OLWETHU_WANTS_HOME, 'Olwethu wants to stay home.'),
    ], 1),
    _sentence_completion('Olwethu goes to ..........', ['School', 'The beach'], 'School', OLWETHU_GOING_TO_SCHOOL, 'Olwethu going to school'),
    _sentence_completion('Olwethu has new ..........', ['Shoes', 'Toys'], 'Shoes', OLWETHU_GETS_READY, 'Olwethu wearing new shoes'),
    _sentence_completion('Olwethu feels .......... at first.', ['Scared', 'Happy'], 'Scared', OLWETHU_WANTS_HOME, 'Olwethu feeling scared at first'),
]


BONGI_FAMILY = _panel(BONGI_STORYBOARD, 1)
BONGI_HELPS_DAD = _panel(BONGI_STORYBOARD, 3)
BONGI_READS = _panel(BONGI_STORYBOARD, 4)
BONGI_WAITS_OUTSIDE = _panel(BONGI_STORYBOARD, 5)
BONGI_HUGS_GRANDPARENTS = _panel(BONGI_STORYBOARD, 6)

BONGI_WAITS_ACTIVITIES = [
    _phonics('F A _ I L Y', 'family', ['N', 'M', 'L'], 'M', BONGI_FAMILY),
    _phonics('Y _ R D', 'yard', ['A', 'E', 'O'], 'A', BONGI_HELPS_DAD),
    _phonics('H _ G G E D', 'hugged', ['A', 'E', 'U'], 'U', BONGI_HUGS_GRANDPARENTS),
    _picture_match('Bongi helped Dad.', [
        _picture(BONGI_READS, 'Bongi reads a picture book.'),
        _picture(BONGI_HELPS_DAD, 'Bongi helps Dad in the yard.'),
        _picture(BONGI_HUGS_GRANDPARENTS, 'Bongi hugs her grandparents.'),
    ], 2),
    _picture_match('Bongi read a picture book.', [
        _picture(BONGI_HELPS_DAD, 'Bongi helps Dad in the yard.'),
        _picture(BONGI_HUGS_GRANDPARENTS, 'Bongi hugs her grandparents.'),
        _picture(BONGI_READS, 'Bongi reads a picture book.'),
    ], 3),
    _picture_match('Bongi hugged Granny and Grandpa.', [
        _picture(BONGI_HUGS_GRANDPARENTS, 'Bongi hugs her grandparents.'),
        _picture(BONGI_HELPS_DAD, 'Bongi helps Dad in the yard.'),
        _picture(BONGI_WAITS_OUTSIDE, 'Bongi waits outside.'),
    ], 1),
    _sentence_completion('Bongi waits ..........', ['Outside', 'Inside'], 'Outside', BONGI_WAITS_OUTSIDE, 'Bongi waiting outside'),
    _sentence_completion('Bongi hugs ..........', ['Granny and Grandpa', 'The teacher'], 'Granny and Grandpa', BONGI_HUGS_GRANDPARENTS, 'Bongi hugging Granny and Grandpa'),
    _sentence_completion('Bongi is ..........', ['Happy', 'Sad'], 'Happy', BONGI_FAMILY, 'Bongi feeling happy'),
]


GRADE_ONE_ACTIVITY_BLUEPRINTS = {
    "Lerato's Fruit Basket": LERATOS_FRUIT_BASKET_ACTIVITIES,
    'A Very Hot Day': A_VERY_HOT_DAY_ACTIVITIES,
    'Ben Goes to School': BEN_GOES_TO_SCHOOL_ACTIVITIES,
    "Olwethu's First Day": OLWETHUS_FIRST_DAY_ACTIVITIES,
    'Bongi Waits': BONGI_WAITS_ACTIVITIES,
}
