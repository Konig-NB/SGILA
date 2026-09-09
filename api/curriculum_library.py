"""Additional CAPS-aligned stories used to complete the Grades 1-4 library."""

import json

from api.grade1_activity_blueprints import (
    BEN_GOES_TO_SCHOOL_ACTIVITIES,
    BONGI_WAITS_ACTIVITIES,
    OLWETHUS_FIRST_DAY_ACTIVITIES,
)


STORYBOARD_IMAGES = {
    'A Very Hot Day': ('g1_hot_storyboard.png', 3),
    'Ben Goes to School': ('g1_ben_storyboard.png', 1),
    "Olwethu's First Day": ('g1_olwethu_storyboard.png', 5),
    'Bongi Waits': ('g1_bongi_storyboard.png', 6),
    "A Dog's Life": ('g2_dog_storyboard.png', 1),
    'A New Baby': ('g2_baby_storyboard.png', 4),
    'The School Shed Is on Fire': ('g2_fire_storyboard.png', 5),
    "Dan's Bad Week": ('g2_dan_storyboard.png', 6),
    'Spring Day Surprise': ('g2_spring_storyboard.png', 1),
    "Mandu's Secret Diary": ('g3_mandu_storyboard.png', 1),
    'Soccer Trouble': ('g3_soccer_storyboard.png', 6),
    'The River Mistake': ('g3_river_storyboard.png', 1),
    'Stage Fright': ('g3_stage_storyboard.png', 3),
    'The Juice Spill': ('g3_juice_storyboard.png', 1),
    "Mandu's Running Shoes": ('g4_mandu_shoes_storyboard.png', 2),
    'Why Mapula Missed School': ('g4_mapula_storyboard.png', 4),
    'Best Friends to the Rescue': ('g4_rescue_storyboard.png', 3),
    'The Terrible Twins': ('g4_twins_storyboard.png', 4),
    "Frog and Crow's Wrong Message": ('g4_message_storyboard.png', 3),
}


def _page(number, text, image, words):
    return (number, text, f'/static/img/caps/{image}', words)


def _choice(skill, question, options, answer):
    return {
        'activity_type': 'multiple_choice',
        'skill': skill,
        'question': question,
        'options': options,
        'correct_answer': answer,
    }


def _true_false(skill, question, answer):
    return {
        'activity_type': 'true_false',
        'skill': skill,
        'question': question,
        'correct_answer': answer,
    }


def _oral(skill, question, answer):
    return {
        'activity_type': 'oral_response',
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


def _reasoning(skill, question, answer):
    return {
        'activity_type': 'reasoning',
        'skill': skill,
        'question': question,
        'correct_answer': answer,
    }


def _prediction(question, answer):
    return {
        'activity_type': 'prediction',
        'skill': 'prediction',
        'question': question,
        'correct_answer': answer,
    }


def _open(skill, question, answer):
    return {
        'activity_type': 'open_ended',
        'skill': skill,
        'question': question,
        'correct_answer': answer,
    }


def _grouped(activity, number, title):
    grouped = dict(activity)
    grouped['group_number'] = number
    grouped['group_title'] = title
    return grouped


MANDUS_SECRET_DIARY_ACTIVITIES = [
    _grouped(_choice(
        'literal_comprehension',
        'What did Mandu write in her diary every day?',
        [
            'What she did during the day and her secrets',
            'Her homework',
            'Letters to Anna',
            'Stories about Zola',
        ],
        'What she did during the day and her secrets',
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'literal_comprehension',
        'Where did Mandu decide to hide her diary?',
        ['In her school bag', 'Under her bed', 'In the kitchen', 'Under a tree'],
        'Under her bed',
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'literal_comprehension',
        'Who found the diary lying wide open on the floor?',
        ['Anna', 'Thabo', 'Mandu', "Mandu's mother"],
        'Mandu',
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'literal_comprehension',
        'What was the first clue the girls found on the diary?',
        ['Dirty fingerprints', 'A torn page', 'A wet patch', 'A name written inside'],
        'Dirty fingerprints',
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'inference',
        "Why couldn't Thabo have been the one reading the diary?",
        [
            'He was at soccer practice',
            'He was too young to read',
            'He was visiting his grandmother',
            "He doesn't like diaries",
        ],
        'He was too young to read',
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'literal_comprehension',
        'What was the second clue Mandu found in the diary?',
        ['A dog collar', 'A blond hair', 'A muddy footprint', 'A drawing'],
        'A blond hair',
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'inference',
        'Why did Mandu look suspiciously at Anna?',
        [
            'Anna was carrying the diary',
            "Anna has blond hair, and everyone in Mandu's family has black hair",
            'Anna admitted to reading it',
            'Anna was hiding something behind her back',
        ],
        "Anna has blond hair, and everyone in Mandu's family has black hair",
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'literal_comprehension',
        'What did the girls sprinkle on the floor to set their trap?',
        ['Water', 'Sand', 'Flour', 'Sugar'],
        'Flour',
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'literal_comprehension',
        'Who turned out to be the real diary reader?',
        ['Thabo', 'Anna', 'Zola the dog', "Mandu's mother"],
        'Zola the dog',
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'literal_comprehension',
        'What advice did Anna give Mandu at the end of the story?',
        [
            'To stop keeping a diary',
            'To find a much better hiding place for her diary',
            'To tell her mother',
            'To lock her bedroom door',
        ],
        'To find a much better hiding place for her diary',
    ), 1, 'Comprehension Questions'),
    _grouped(_reasoning(
        'text_to_self',
        'Do you think the flour trap was a clever idea? Why or why not?',
        'Yes, it was clever because the flour showed the paw prints. Any clear opinion supported by a reason is acceptable.',
    ), 1, 'Comprehension Questions'),
    _grouped(_choice(
        'inference',
        'How do you think Mandu felt when she saw the paw prints in the flour?',
        ['Angry', 'Relieved and amused', 'Frightened', 'Bored'],
        'Relieved and amused',
    ), 1, 'Comprehension Questions'),
    _grouped(_sequence(
        'Put the story moments in the order in which they happened.',
        [
            'Mandu writes her secrets in her diary every day.',
            'Mandu hides her diary under her bed.',
            'Mandu finds her diary lying open on the floor.',
            'Anna and Mandu find a dirty fingerprint and a blond hair.',
            'The girls sprinkle flour on the floor as a trap.',
            'They discover paw prints - Zola the dog was the culprit!',
        ],
    ), 2, 'Story Sequencer'),
    _grouped(_true_false(
        'literal_comprehension',
        'Mandu hid her diary under her pillow.',
        'False',
    ), 3, 'True or False Detective'),
    _grouped(_true_false(
        'literal_comprehension',
        "Mandu's dog is called Zola.",
        'True',
    ), 3, 'True or False Detective'),
    _grouped(_true_false(
        'literal_comprehension',
        'Thabo is older than Mandu.',
        'False',
    ), 3, 'True or False Detective'),
    _grouped(_true_false(
        'literal_comprehension',
        'Anna has blond hair.',
        'True',
    ), 3, 'True or False Detective'),
    _grouped(_true_false(
        'literal_comprehension',
        'The girls used flour to catch the culprit.',
        'True',
    ), 3, 'True or False Detective'),
    _grouped(_true_false(
        'literal_comprehension',
        "Everybody in Mandu's family has blond hair.",
        'False',
    ), 3, 'True or False Detective'),
    {
        'activity_type': 'matching',
        'skill': 'vocabulary_in_context',
        'question': 'Match each tricky word to its meaning.',
        'options': {
            'prompts': [
                {'key': 'secret', 'text': 'secret'},
                {'key': 'suspiciously', 'text': 'suspiciously'},
                {'key': 'clue', 'text': 'clue'},
                {'key': 'culprit', 'text': 'culprit'},
                {'key': 'examined', 'text': 'examined'},
            ],
            'choices': [
                {'key': 'a', 'text': 'looked at something closely and carefully'},
                {'key': 'b', 'text': 'a piece of information that helps solve a mystery'},
                {'key': 'c', 'text': 'the person or animal who did something wrong'},
                {'key': 'd', 'text': "something you don't want anyone else to know"},
                {'key': 'e', 'text': "in a way that shows you don't fully trust someone"},
            ],
        },
        'correct_answer': json.dumps({
            'secret': 'd',
            'suspiciously': 'e',
            'clue': 'b',
            'culprit': 'c',
            'examined': 'a',
        }),
        'group_number': 4,
        'group_title': 'Word Detective',
    },
    *[
        {
            'activity_type': 'cloze',
            'skill': 'vocabulary_in_context',
            'question': question,
            'options': ['diary', 'footprints', 'blond', 'flour', 'secret'],
            'correct_answer': answer,
            'group_number': 5,
            'group_title': 'Fill in the Blank',
        }
        for question, answer in [
            ('Mandu wrote in her ____ every day.', 'diary'),
            ('She sprinkled ____ on the floor to catch the culprit.', 'flour'),
            ('Anna has ____ hair.', 'blond'),
            ('The next morning, they found ____ in the flour.', 'footprints'),
            ('Mandu kept ____ things that she did not want anyone to see.', 'secret'),
        ]
    ],
    _grouped(_choice(
        'character_motivation',
        'How did Mandu feel when she found her diary lying open on the floor?',
        ['Excited', 'Shocked and upset', 'Bored', 'Proud'],
        'Shocked and upset',
    ), 6, 'How Did They Feel?'),
    _grouped(_choice(
        'character_motivation',
        'How did Mandu feel when she saw the paw prints and realised Zola was the culprit?',
        ['Angry', 'Relieved and amused', 'Scared', 'Sad'],
        'Relieved and amused',
    ), 6, 'How Did They Feel?'),
    {
        'activity_type': 'reasoning',
        'skill': 'text_to_self',
        'question': 'Write your own diary entry.',
        'options': {
            'writing_template': True,
            'prompt': 'Write about a time you had a secret, like Mandu.',
            'feelings': ['happy', 'grumpy', 'surprised', 'proud', 'scared'],
        },
        'correct_answer': (
            'Dear Diary, today I felt ... because ... . The best part of my day was ... . '
            'Next time I would like to ... .'
        ),
        'group_number': 7,
        'group_title': 'My Diary',
    },
]


EXPANDED_STORIES = [
    {
        'title': 'Ben Goes to School',
        'grade': 1,
        'focus_word': 'School',
        'visual_options': 'School,Beach,Shop,Farm',
        'pages': [
            _page(
                1,
                'Jabu walked to school after the holidays. He felt sad because he could not play with Ben. '
                'Jabu did not see that his dog was following him.',
                'g1_ben_02.png',
                'Jabu,school,sad,following',
            ),
            _page(
                2,
                'At school, Jabu greeted his friends. Ben hid nearby, but Jabu was too busy to notice him.',
                'g1_ben_03.png',
                'friends,hid,notice',
            ),
            _page(
                3,
                'Mrs Moleleki taught the class a new song. The children sang together while Ben stayed quiet.',
                'g1_ben_03.png',
                'teacher,class,song,quiet',
            ),
            _page(
                4,
                'At break, Jabu kicked a ball with his friends. Ben ran onto the field and chased the ball. '
                'Jabu was happy to see him.',
                'g1_ben_04.png',
                'break,ball,field,happy',
            ),
            _page(
                5,
                'Jabu played with Ben and his friends. It was a good day at school.',
                'g1_ben_05.png',
                'played,friends,good',
            ),
        ],
        'activities': BEN_GOES_TO_SCHOOL_ACTIVITIES,
    },
    {
        'title': "Olwethu's First Day",
        'grade': 1,
        'focus_word': 'Friend',
        'visual_options': 'Friend,Dog,Bus,Ball',
        'pages': [
            _page(
                1,
                'Olwethu was going to school for the first time. She felt scared and could not sleep well.',
                'g1_olwethu_01.png',
                'school,first,scared,sleep',
            ),
            _page(
                2,
                'Gogo, Mother and Zinzi helped Olwethu get ready. They showed her new uniform, shoes and school bag.',
                'g1_olwethu_02.png',
                'Gogo,Mother,uniform,shoes',
            ),
            _page(
                3,
                'Olwethu cried on the way to school. She wanted to stay at home and play all day.',
                'g1_olwethu_03.png',
                'cried,home,play',
            ),
            _page(
                4,
                'In the classroom, Olwethu sat next to a girl with the same hairstyle. They smiled at each other '
                'and learned a new song.',
                'g1_olwethu_04.png',
                'classroom,girl,smiled,song',
            ),
            _page(
                5,
                'At the end of the day, Olwethu did not want to leave. School had been fun, and she had made a friend.',
                'g1_olwethu_05.png',
                'leave,fun,friend',
            ),
        ],
        'activities': OLWETHUS_FIRST_DAY_ACTIVITIES,
    },
    {
        'title': 'Bongi Waits',
        'grade': 1,
        'focus_word': 'Family',
        'visual_options': 'Family,Teacher,Doctor,Driver',
        'pages': [
            _page(
                1,
                'Bongi was excited. Granny and Grandpa were coming to visit from far away. Her family planned a braai.',
                'g1_bongi_01.png',
                'excited,Granny,Grandpa,family',
            ),
            _page(
                2,
                'Bongi helped Dad prepare the yard. Then she skipped rope with Gugu and Anna while she waited.',
                'g1_bongi_02.png',
                'helped,yard,skipped,waited',
            ),
            _page(
                3,
                'Gugu and Anna built a tower. Bongi read a picture book to her baby brother, Siya, but she kept thinking about her grandparents.',
                'g1_bongi_03.png',
                'tower,read,baby,thinking',
            ),
            _page(
                4,
                'Mother said Granny and Grandpa were almost there. Everyone went outside to wait.',
                'g1_bongi_04.png',
                'almost,outside,wait',
            ),
            _page(
                5,
                'Dad called, "They are here!" Bongi ran outside and hugged Granny and Grandpa. The braai began.',
                'g1_bongi_05.png',
                'called,ran,hugged,braai',
            ),
        ],
        'activities': BONGI_WAITS_ACTIVITIES,
    },
    {
        'title': 'The School Shed Is on Fire',
        'grade': 2,
        'focus_word': 'Fire',
        'visual_options': 'Fire,Rain,Wind,Snow',
        'pages': [
            _page(
                1,
                'The class smelled smoke. Ben the dog sniffed the air. Then everyone saw that the school shed '
                'was on fire.',
                'g2_fire_01.png',
                'smoke,sniffed,shed,fire',
            ),
            _page(
                2,
                'The teacher led the learners to stand in a line under the trees. They felt afraid. '
                'The teacher phoned the fire service.',
                'g2_fire_02.png',
                'teacher,line,afraid,phoned',
            ),
            _page(
                3,
                'Six firefighters arrived. They wore masks and strong belts and carried equipment.',
                'g2_fire_03.png',
                'firefighters,masks,belts,equipment',
            ),
            _page(
                4,
                'The bright red fire engine brought a thick hose. The firefighters sprayed water on the flames '
                'until the fire was out. The shed was saved.',
                'g2_fire_04.png',
                'engine,hose,flames,saved',
            ),
        ],
        'activities': [
            _choice(
                'literal_comprehension',
                'What did the class smell?',
                ['Smoke', 'Flowers', 'Food'],
                'Smoke',
            ),
            _choice(
                'vocabulary_in_context',
                'What does afraid mean here?',
                ['Feeling scared', 'Feeling hungry', 'Feeling sleepy'],
                'Feeling scared',
            ),
            _sequence(
                'Put the rescue in order.',
                [
                    'The class smells smoke.',
                    'The teacher phones for help.',
                    'The firefighters put out the fire.',
                ],
            ),
            _reasoning(
                'inference',
                'Why did the class stand away from the shed?',
                'They stood away from the shed so they would be safe from the fire and smoke.',
            ),
            _true_false(
                'literal_comprehension',
                'The firefighters came in a red fire engine.',
                'True',
            ),
        ],
    },
    {
        'title': "Dan's Bad Week",
        'grade': 2,
        'focus_word': 'Week',
        'visual_options': 'Week,Minute,Season,Year',
        'pages': [
            _page(
                1,
                'On Monday, Dan woke up late. He missed the bus and arrived late for school.',
                'g2_dan_01.png',
                'Monday,late,missed,bus',
            ),
            _page(
                2,
                'On Tuesday, Dan woke up early, but he left his school bag on the bus. He only had his soccer ball.',
                'g2_dan_02.png',
                'Tuesday,early,bag,bus',
            ),
            _page(
                3,
                'On Wednesday, Dan held his bag tightly. He got onto the wrong bus and arrived at the wrong school.',
                'g2_dan_03.png',
                'Wednesday,wrong,arrived',
            ),
            _page(
                4,
                'On Thursday, Dan could not find his uniform. He went to school in his swimming clothes.',
                'g2_dan_04.png',
                'Thursday,uniform,swimming',
            ),
            _page(
                5,
                'On Friday, Dan arrived early with his bag and uniform. He was so tired that he fell asleep in class.',
                'g2_dan_05.png',
                'Friday,early,tired,asleep',
            ),
            _page(
                6,
                'Dan even tried to go to school on Saturday. The gate was locked. On Sunday, he fell into a cake '
                'at a family party. Dan hoped the next week would be better.',
                'g2_dan_06.png',
                'Saturday,locked,Sunday,cake',
            ),
        ],
        'activities': [
            _choice(
                'literal_comprehension',
                'What happened on Monday?',
                ['Dan missed the bus.', 'Dan lost his uniform.', 'Dan fell into a cake.'],
                'Dan missed the bus.',
            ),
            _choice(
                'vocabulary_in_context',
                'The gate was locked. What does locked mean?',
                ['It could not be opened.', 'It was painted.', 'It was very small.'],
                'It could not be opened.',
            ),
            _sequence(
                'Put these mistakes in order.',
                [
                    'Dan misses the bus.',
                    'Dan loses his bag.',
                    'Dan goes to the wrong school.',
                    'Dan wears swimming clothes.',
                ],
            ),
            _reasoning(
                'inference',
                'Why did Dan go to school on Saturday?',
                'Dan wanted one day when he did everything correctly and forgot that school was closed.',
            ),
            _true_false(
                'literal_comprehension',
                'Dan went to the wrong school on Wednesday.',
                'True',
            ),
        ],
    },
    {
        'title': 'Spring Day Surprise',
        'grade': 2,
        'focus_word': 'Spring',
        'visual_options': 'Spring,Winter,Night,Lunch',
        'pages': [
            _page(
                1,
                'Olwethu and Katekani walked to school in the warm sun. They saw orange butterflies and birds '
                'building a nest.',
                'g2_spring_01.png',
                'warm,butterflies,birds,nest',
            ),
            _page(
                2,
                'Their teacher wrote 1 September on the board. It was Spring Day. Katekani remembered that her '
                'brother liked to splash water on people.',
                'g2_spring_02.png',
                'September,Spring,remembered,splash',
            ),
            _page(
                3,
                'After school, the girls played outside. Katekani forgot about the Spring Day water game.',
                'g2_spring_03.png',
                'after,played,forgot,water',
            ),
            _page(
                4,
                'Then Katekani remembered. She and Olwethu hurried home, looking carefully for her brother.',
                'g2_spring_04.png',
                'remembered,hurried,carefully',
            ),
            _page(
                5,
                'Near the house, they heard giggling. Katekani saw her brother and his friends holding buckets.',
                'g2_spring_05.png',
                'giggling,brother,buckets',
            ),
            _page(
                6,
                'The boys splashed the girls with water. Everyone laughed in the warm spring sunshine.',
                'g2_spring_06.png',
                'splashed,laughed,warm,sunshine',
            ),
        ],
        'activities': [
            _choice(
                'literal_comprehension',
                'What date was Spring Day?',
                ['1 September', '1 January', '1 June'],
                '1 September',
            ),
            _choice(
                'vocabulary_in_context',
                'What does hurried mean?',
                ['Moved quickly', 'Sat quietly', 'Walked backwards'],
                'Moved quickly',
            ),
            _sequence(
                'Put the Spring Day events in order.',
                [
                    'The girls walk to school.',
                    'They play after school.',
                    'They hurry home.',
                    'The boys splash them.',
                ],
            ),
            _reasoning(
                'inference',
                'Why did the girls hurry home?',
                'They wanted to reach home before Katekani\'s brother could splash them with water.',
            ),
            _true_false(
                'literal_comprehension',
                'The girls saw butterflies on the way to school.',
                'True',
            ),
        ],
    },
    {
        'title': 'Soccer Trouble',
        'grade': 3,
        'focus_word': 'Goal',
        'visual_options': 'Goal,Stage,River,Desk',
        'pages': [
            _page(
                1,
                'John returned to school after an action-packed holiday. He was pleased to see Jabu, Robert '
                'and Shawn again. After school, they went to soccer practice.',
                'g3_soccer_01.png',
                'returned,holiday,practice',
            ),
            _page(
                2,
                'Coach Jones told John to look at the goal post and kick the ball. John saw Mary watching from '
                'the side-line and decided to impress her with a cartwheel and a handstand.',
                'g3_soccer_01.png',
                'coach,goal,side-line,impress',
            ),
            _page(
                3,
                'John kicked very hard. The ball flew straight up while John fell onto his back. The ball came '
                'down and bumped his nose.',
                'g3_soccer_02.png',
                'kicked,flew,fell,bumped',
            ),
            _page(
                4,
                'John felt embarrassed because his trick had gone wrong. He realised that showing off had stopped '
                'him from listening to his coach.',
                'g3_soccer_02.png',
                'embarrassed,showing off,listening',
            ),
        ],
        'activities': [
            _choice(
                'literal_comprehension',
                'What did Coach Jones tell John to do?',
                ['Look at the goal and kick.', 'Sit on the side-line.', 'Carry the goal post.'],
                'Look at the goal and kick.',
            ),
            _choice(
                'vocabulary_in_context',
                'What does impress mean in this story?',
                ['Make someone admire him', 'Ask someone for help', 'Hide from the coach'],
                'Make someone admire him',
            ),
            _sequence(
                'Put the practice events in order.',
                [
                    'The coach gives an instruction.',
                    'John sees Mary watching.',
                    'John tries a trick.',
                    'The ball bumps his nose.',
                ],
            ),
            _reasoning(
                'inference',
                'Why did John stop following the coach\'s instruction?',
                'John became distracted because he wanted Mary to notice and admire him.',
            ),
            _prediction(
                'What should John do at the next practice, and why?',
                'He should listen to the coach and focus on the goal so that he can play safely and improve.',
            ),
            _open(
                'summarising',
                'What is the main lesson of this story?',
                'Trying to show off distracted John from listening and led to an embarrassing mistake.',
            ),
        ],
    },
    {
        'title': 'The River Mistake',
        'grade': 3,
        'focus_word': 'River',
        'visual_options': 'River,Road,Classroom,Kitchen',
        'pages': [
            _page(
                1,
                'John\'s mother had warned him never to swim in the river. One very hot Friday, John and Robert '
                'ignored the warning and went swimming.',
                'g3_river_01.png',
                'warned,river,ignored,swimming',
            ),
            _page(
                2,
                'The boys left their clothes on the rocks. They splashed and played until the sun began to set.',
                'g3_river_01.png',
                'clothes,rocks,splashed,set',
            ),
            _page(
                3,
                'When they climbed out, their clothes were gone. Goats were chewing them, and one goat ran away '
                'with John\'s shorts.',
                'g3_river_02.png',
                'gone,goats,chewing,shorts',
            ),
            _page(
                4,
                'The boys covered themselves and ran home. John\'s mother was furious because he had disobeyed '
                'her and put himself in danger.',
                'g3_river_02.png',
                'covered,furious,disobeyed,danger',
            ),
        ],
        'activities': [
            _choice(
                'literal_comprehension',
                'Where did the boys leave their clothes?',
                ['On the rocks', 'Under a bed', 'In a bag'],
                'On the rocks',
            ),
            _choice(
                'vocabulary_in_context',
                'John\'s mother was furious. How did she feel?',
                ['Very angry', 'Very proud', 'Very tired'],
                'Very angry',
            ),
            _sequence(
                'Put the river events in order.',
                [
                    'The boys leave their clothes.',
                    'They swim in the river.',
                    'Goats eat the clothes.',
                    'The boys run home.',
                ],
            ),
            _reasoning(
                'inference',
                'Why was Mother angry for more than one reason?',
                'John disobeyed her warning and also put himself in danger by swimming in the river.',
            ),
            _prediction(
                'What will John probably do on the next hot day? Explain.',
                'He will probably avoid the river or ask an adult because this mistake brought danger and trouble.',
            ),
            _open(
                'summarising',
                'Summarise the problem and result in one sentence.',
                'John and Robert ignored a safety warning, and goats ate their clothes while they swam.',
            ),
        ],
    },
    {
        'title': 'Stage Fright',
        'grade': 3,
        'focus_word': 'Stage',
        'visual_options': 'Stage,Beach,Hospital,Bus',
        'pages': [
            _page(
                1,
                'John had practised for the school concert for three weeks. He was playing the wolf in the story '
                'of the Seven Kid Goats.',
                'g3_stage_01.png',
                'practised,concert,wolf,story',
            ),
            _page(
                2,
                'When John stepped onto the stage, his mind went blank. He could see his family in the audience, '
                'but he could not remember his lines.',
                'g3_stage_01.png',
                'stage,blank,audience,lines',
            ),
            _page(
                3,
                'John stammered. His teacher prompted him, but his voice would not work properly because he was '
                'so nervous.',
                'g3_stage_02.png',
                'stammered,prompted,voice,nervous',
            ),
            _page(
                4,
                'As John left the stage, he accidentally knocked over the goat house. He felt embarrassed, but '
                'he knew he had still been brave enough to try.',
                'g3_stage_02.png',
                'accidentally,embarrassed,brave,try',
            ),
        ],
        'activities': [
            _choice(
                'literal_comprehension',
                'Which character did John play?',
                ['The wolf', 'A teacher', 'A goat farmer'],
                'The wolf',
            ),
            _choice(
                'vocabulary_in_context',
                'His mind went blank. What does blank mean here?',
                ['He forgot his words.', 'He fell asleep.', 'He became angry.'],
                'He forgot his words.',
            ),
            _sequence(
                'Put the concert events in order.',
                [
                    'John practises his lines.',
                    'John walks onto the stage.',
                    'The teacher prompts him.',
                    'John knocks over the house.',
                ],
            ),
            _reasoning(
                'inference',
                'Why could John forget after practising for weeks?',
                'Seeing the audience made John extremely nervous, so stage fright stopped him from remembering.',
            ),
            _prediction(
                'What could John do before his next concert?',
                'He could practise in front of people and use slow breathing so the audience feels more familiar.',
            ),
            _open(
                'summarising',
                'What is this story mostly about?',
                'John experiences stage fright during a concert even though he prepared carefully.',
            ),
        ],
    },
    {
        'title': 'The Juice Spill',
        'grade': 3,
        'focus_word': 'Exam',
        'visual_options': 'Exam,Concert,Picnic,Match',
        'pages': [
            _page(
                1,
                'John was writing an English exam. He felt nervous, and his mouth became dry while he worked.',
                'g3_juice_01.png',
                'English,exam,nervous,dry',
            ),
            _page(
                2,
                'John carefully took out his juice bottle. He hoped the teacher would not notice because drinks '
                'were not allowed during the exam.',
                'g3_juice_01.png',
                'carefully,juice,hoped,allowed',
            ),
            _page(
                3,
                'The teacher looked at John. He knocked over the bottle, and juice spread across his exam book '
                'and Robert\'s book.',
                'g3_juice_02.png',
                'knocked,spread,book',
            ),
            _page(
                4,
                'John was sent to the principal\'s office. The principal phoned his mother. John wished he had '
                'asked for permission instead of hiding the bottle.',
                'g3_juice_02.png',
                'principal,phoned,permission,hiding',
            ),
        ],
        'activities': [
            _choice(
                'literal_comprehension',
                'What was John writing?',
                ['An English exam', 'A shopping list', 'A birthday card'],
                'An English exam',
            ),
            _choice(
                'vocabulary_in_context',
                'John felt nervous. What does nervous mean here?',
                ['Worried and uneasy', 'Calm and relaxed', 'Bored and sleepy'],
                'Worried and uneasy',
            ),
            _sequence(
                'Put the events in order.',
                [
                    'John feels thirsty.',
                    'He takes out the bottle.',
                    'The juice spills.',
                    'The principal phones home.',
                ],
            ),
            _reasoning(
                'inference',
                'Why did John try to hide the bottle?',
                'He knew drinks were not allowed and feared that the teacher would stop him.',
            ),
            _prediction(
                'What should John do if he feels thirsty in the next exam?',
                'He should raise his hand and ask the teacher for permission before drinking.',
            ),
            _open(
                'summarising',
                'Summarise how one choice caused the problem.',
                'John hid a drink during the exam, then spilled it when the teacher noticed him.',
            ),
        ],
    },
      {
          'title': "Mandu's Running Shoes",
        'grade': 4,
        'focus_word': 'Running Shoes',
        'visual_options': 'Running Shoes,Sandals,Boots,Slippers',
        'pages': [
              _page(
                  1,
                  'Mandu was a Grade 4 learner at Greenway Primary School in Durban. She was an excellent runner, '
                  'but other children teased her because she had no running shoes. The hot ground often hurt her feet.',
                'g4_mandu_shoes_01.png',
                'trained,excellent,runner,ground',
            ),
              _page(
                  2,
                  'On Saturday, Mandu took the money she had saved to a sports shop in town. She found the running '
                  'shoes she wanted, but her savings were not enough. Mandu looked at them sadly.',
                'g4_mandu_shoes_02.png',
                'saved,afford,owner,challenge',
            ),
              _page(
                  3,
                  'Mrs Masondo, the shop owner, offered Mandu a deal. If Mandu won the school race, she could have '
                  'the shoes for free. If she did not win, she would have to pay for them.',
                'g4_mandu_shoes_03.png',
                'practised,ached,effort,goal',
            ),
              _page(
                  4,
                  'Mandu practised every day until her legs ached. When she wanted to stop, she told herself, '
                  '"I must keep going. I must not give up!" She was determined to win.',
                'g4_mandu_shoes_04.png',
                'nervous,signal,focused,runners',
            ),
              _page(
                  5,
                  'Before the race Mandu felt nervous and her heart was pounding. Once she started running, she '
                  'forgot her fear. She crossed the finish line first, and Mrs Masondo joyfully gave her the shoes. '
                  'Mandu felt grateful and learned that determination can help a dream come true.',
                'g4_mandu_shoes_05.png',
                'finish,congratulated,promise,perseverance',
            ),
          ],
          'activities': [
              {
                  **_choice(
                      'literal_comprehension',
                      'In which grade was Mandu, and at which school did she learn?',
                      [
                          'Grade 3 at Greenway Primary School in Durban',
                          'Grade 5 at Durban Sports School',
                          'Grade 4 at Greenway Primary School in Durban',
                          'Grade 4 at Masondo Primary School in Cape Town',
                      ],
                      'Grade 4 at Greenway Primary School in Durban',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  **_choice(
                      'literal_comprehension',
                      'Why did the other children tease Mandu?',
                      [
                          'She did not have running shoes',
                          'She did not like running',
                          'She always arrived late',
                          'She would not share her lunch',
                      ],
                      'She did not have running shoes',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  **_choice(
                      'literal_comprehension',
                      "Why did Mandu's feet hurt, especially when the ground was hot?",
                      [
                          'Her shoes were too small',
                          'She had fallen during practice',
                          'She ran only on stones',
                          'She had no running shoes to protect them',
                      ],
                      'She had no running shoes to protect them',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  **_choice(
                      'literal_comprehension',
                      'Where did Mandu go on Saturday, and why did she go there?',
                      [
                          'To school to practise with her teacher',
                          'To a sports shop to look for shoes with her savings',
                          'To a market to sell her old shoes',
                          'To the race track to collect a medal',
                      ],
                      'To a sports shop to look for shoes with her savings',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  **_choice(
                      'literal_comprehension',
                      'Why did Mandu feel very sad when she looked at the running shoes?',
                      [
                          'The shop did not have her size',
                          'The shoes were the wrong colour',
                          'She did not have enough money to buy them',
                          'Mrs Masondo would not speak to her',
                      ],
                      'She did not have enough money to buy them',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  **_choice(
                      'literal_comprehension',
                      'What deal did Mrs Masondo offer Mandu?',
                      [
                          'Work in the shop for one afternoon',
                          'Win the race and receive the shoes for free',
                          'Borrow the shoes and return them after the race',
                          'Save money until the following year',
                      ],
                      'Win the race and receive the shoes for free',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  **_choice(
                      'inference',
                      'Which TWO details best show that Mandu was determined to win?',
                      [
                          'She visited town and looked through the shop window',
                          'She felt nervous and listened for the starting signal',
                          'She saved coins and spoke to the other runners',
                          'She practised every day and told herself not to give up',
                      ],
                      'She practised every day and told herself not to give up',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  **_choice(
                      'character_motivation',
                      'How did Mandu feel before the race, and what changed once she started running?',
                      [
                          'She felt nervous, then forgot her fear',
                          'She felt angry, then became bored',
                          'She felt excited, then wanted to stop',
                          'She felt calm, then became frightened',
                      ],
                      'She felt nervous, then forgot her fear',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  **_choice(
                      'inference',
                      'Which answer best explains why Mrs Masondo was kind to Mandu?',
                      [
                          'She let Mandu take anything from the shop',
                          'She cancelled the race so Mandu would not lose',
                          'She gave Mandu a fair chance to earn the shoes through effort',
                          'She paid the other runners to slow down',
                      ],
                      'She gave Mandu a fair chance to earn the shoes through effort',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  **_choice(
                      'summarising',
                      "What is the main lesson of Mandu's story?",
                      [
                          'Winning is more important than being kind',
                          'Hard work and determination can help you reach a goal',
                          'Expensive shoes always make someone a better runner',
                          'Children should never enter a race without money',
                      ],
                      'Hard work and determination can help you reach a goal',
                  ),
                  'group_number': 1,
                  'group_title': 'Comprehension Questions',
              },
              {
                  'activity_type': 'crossword',
                  'skill': 'vocabulary_in_context',
                  'question': 'Complete the crossword using words from the story.',
                  'options': {
                      'rows': 7,
                      'columns': 8,
                      'entries': [
                          {'key': '1-across', 'number': 1, 'direction': 'Across', 'row': 0, 'column': 1, 'length': 7, 'clue': 'Mandu did this every day to get faster and stronger.'},
                          {'key': '2-down', 'number': 2, 'direction': 'Down', 'row': 0, 'column': 3, 'length': 7, 'clue': 'How Mandu felt just before the race began.'},
                          {'key': '3-across', 'number': 3, 'direction': 'Across', 'row': 2, 'column': 3, 'length': 4, 'clue': 'A contest to see who is the fastest.'},
                          {'key': '4-across', 'number': 4, 'direction': 'Across', 'row': 4, 'column': 1, 'length': 5, 'clue': 'Mandu wanted these so that her feet would not hurt.'},
                          {'key': '5-across', 'number': 5, 'direction': 'Across', 'row': 6, 'column': 3, 'length': 3, 'clue': 'How Mandu felt when she could not buy the shoes.'},
                      ],
                  },
                  'correct_answer': json.dumps({
                      '1-across': 'RUNNING',
                      '2-down': 'NERVOUS',
                      '3-across': 'RACE',
                      '4-across': 'SHOES',
                      '5-across': 'SAD',
                  }),
                  'group_number': 2,
                  'group_title': 'Crossword Puzzle',
              },
              {
                  'activity_type': 'matching',
                  'skill': 'vocabulary_in_context',
                  'question': 'Match each word from the story with its meaning.',
                  'options': {
                      'prompts': [
                          {'key': '1', 'text': 'practised'},
                          {'key': '2', 'text': 'grateful'},
                          {'key': '3', 'text': 'nervous'},
                          {'key': '4', 'text': 'joyfully'},
                          {'key': '5', 'text': 'tease'},
                          {'key': '6', 'text': 'ached'},
                          {'key': '7', 'text': 'participants'},
                      ],
                      'choices': [
                          {'key': 'a', 'text': 'hurt or felt pain'},
                          {'key': 'b', 'text': 'worried or afraid before something happens'},
                          {'key': 'c', 'text': 'to make fun of someone in an unkind way'},
                          {'key': 'd', 'text': 'did something again and again to get better at it'},
                          {'key': 'e', 'text': 'people who take part in an activity, such as a race'},
                          {'key': 'f', 'text': 'in a very happy and excited way'},
                          {'key': 'g', 'text': 'feeling thankful'},
                      ],
                  },
                  'correct_answer': json.dumps({
                      '1': 'd',
                      '2': 'g',
                      '3': 'b',
                      '4': 'f',
                      '5': 'c',
                      '6': 'a',
                      '7': 'e',
                  }),
                  'group_number': 3,
                  'group_title': 'Word Detective',
              },
              {
                  'activity_type': 'word_scramble',
                  'skill': 'spelling',
                  'question': 'Unscramble each group of letters to spell the story word correctly.',
                  'options': {
                      'items': [
                          {'key': '1', 'scramble': 'OSHSE'},
                          {'key': '2', 'scramble': 'NIRNGNU'},
                          {'key': '3', 'scramble': 'SIPTRDACE'},
                          {'key': '4', 'scramble': 'TAFERGLU'},
                          {'key': '5', 'scramble': 'USVOREN'},
                          {'key': '6', 'scramble': 'HISNIF'},
                          {'key': '7', 'scramble': 'GNIPUODN'},
                          {'key': '8', 'scramble': 'SESADNS'},
                      ],
                  },
                  'correct_answer': json.dumps({
                      '1': 'SHOES',
                      '2': 'RUNNING',
                      '3': 'PRACTISED',
                      '4': 'GRATEFUL',
                      '5': 'NERVOUS',
                      '6': 'FINISH',
                      '7': 'POUNDING',
                      '8': 'SADNESS',
                  }),
                  'group_number': 4,
                  'group_title': 'Spelling Activity',
              },
          ],
      },
    {
        'title': 'Why Mapula Missed School',
        'grade': 4,
        'focus_word': 'Fire Engine',
        'visual_options': 'Fire Engine,Bus,Ambulance,Tractor',
        'pages': [
            _page(
                1,
                'Mapula missed school after her young brother, Thami, played with matches near the family\'s '
                'paraffin stove. Children had been warned never to touch either item.',
                'g4_mapula_01.png',
                'missed,matches,paraffin,warned',
            ),
            _page(
                2,
                'Thami knocked the lit stove onto the carpet. Smoke filled the room and flames spread quickly. '
                'Mapula understood that they had to leave at once.',
                'g4_mapula_02.png',
                'knocked,carpet,smoke,flames',
            ),
            _page(
                3,
                'Mapula carried Thami outside and called to the neighbours for help. A neighbour phoned the fire '
                'brigade while Mapula kept her brother safely away from the house.',
                'g4_mapula_03.png',
                'carried,neighbours,brigade,safely',
            ),
            _page(
                4,
                'Firefighters arrived in a fire engine and used long hoses to stop the fire. Some belongings were '
                'damaged, but Mapula and Thami were safe when their parents returned.',
                'g4_mapula_04.png',
                'firefighters,engine,hoses,damaged',
            ),
            _page(
                5,
                'The next day, Mapula helped her mother clean and hung wet blankets in the sun. She would return '
                'to school after helping at home, and the family reviewed their fire-safety rules.',
                'g4_mapula_05.png',
                'blankets,return,reviewed,safety',
            ),
        ],
        'activities': [
            _sequence(
                'Put the emergency events in the correct order.',
                [
                    'Thami knocks over the stove.',
                    'Mapula carries Thami outside.',
                    'A neighbour calls the fire brigade.',
                    'Firefighters put out the fire.',
                ],
            ),
            _choice(
                'literal_comprehension',
                'Who phoned the fire brigade?',
                ['A neighbour', 'Thami', 'Mapula\'s teacher', 'The shop owner'],
                'A neighbour',
            ),
            _choice(
                'vocabulary_in_context',
                'What does reviewed mean on the last page?',
                ['Went over again', 'Forgot completely', 'Wrote for the first time', 'Broke on purpose'],
                'Went over again',
            ),
            _reasoning(
                'inference',
                'Which of Mapula\'s actions shows that she thought quickly?',
                'She moved Thami outside immediately and asked neighbours to call trained firefighters.',
            ),
            _choice(
                'fact_vs_opinion',
                'Which statement is a fact from the story?',
                ['Firefighters used hoses.', 'Mapula has the nicest blankets.', 'Thami is the worst brother.', 'The fire engine was beautiful.'],
                'Firefighters used hoses.',
            ),
            _reasoning(
                'character_motivation',
                'Why did Mapula stay home the next day?',
                'She needed to help her mother clean and dry belongings after the fire.',
            ),
            _open(
                'summarising',
                'State the danger, Mapula\'s response and the outcome in three sentences.',
                'A knocked-over paraffin stove started a fire. Mapula took Thami outside and called for help. Firefighters stopped the fire and both children were safe.',
            ),
        ],
    },
    {
        'title': 'Best Friends to the Rescue',
        'grade': 4,
        'focus_word': 'First Aid Kit',
        'visual_options': 'First Aid Kit,Lunch Box,Toolbox,Suitcase',
        'pages': [
            _page(
                1,
                'Brenda and Mandu were walking home from first-aid class. Their kits were still in their school '
                'bags when they heard someone calling for help near a fruit tree.',
                'g4_rescue_01.png',
                'first-aid,kits,calling,fruit',
            ),
            _page(
                2,
                'Six-year-old Benny had fallen from the tree and was unconscious. His arm was cut. The girls '
                'checked the area, stayed calm and asked an adult to call an ambulance.',
                'g4_rescue_02.png',
                'fallen,unconscious,checked,ambulance',
            ),
            _page(
                3,
                'Brenda and Mandu put on gloves from their first-aid kits. They pressed a clean dressing against '
                'the cut to slow the bleeding and then secured a bandage around Benny\'s arm.',
                'g4_rescue_03.png',
                'gloves,dressing,bleeding,bandage',
            ),
            _page(
                4,
                'The ambulance arrived and the paramedics took over. They praised the girls for calling for help '
                'and using the first-aid skills they had learned.',
                'g4_rescue_04.png',
                'arrived,paramedics,praised,skills',
            ),
            _page(
                5,
                'At Friday assembly, the principal recognised Brenda and Mandu for their teamwork. The friends '
                'were proud that learning a practical skill had helped them support someone in danger.',
                'g4_rescue_05.png',
                'assembly,recognised,teamwork,practical',
            ),
        ],
        'activities': [
            _choice(
                'literal_comprehension',
                'Where had Brenda and Mandu been before they found Benny?',
                ['First-aid class', 'Soccer practice', 'The library', 'A birthday party'],
                'First-aid class',
            ),
            _choice(
                'vocabulary_in_context',
                'What does unconscious mean in this report?',
                ['Not awake or responding', 'Unable to hear a whisper', 'Angry about an accident', 'Ready to climb again'],
                'Not awake or responding',
            ),
            _sequence(
                'Order the girls\' response to the emergency.',
                [
                    'They find Benny beside the tree.',
                    'They ask an adult to call an ambulance.',
                    'They put on gloves and bandage his arm.',
                    'Paramedics arrive and take over.',
                ],
            ),
            _reasoning(
                'inference',
                'Why were the first-aid kits important?',
                'The kits contained gloves, a clean dressing and a bandage that the girls used safely.',
            ),
            _choice(
                'fact_vs_opinion',
                'Which sentence is an opinion?',
                ['Brenda and Mandu were the bravest learners in the country.', 'Benny fell from a tree.', 'An ambulance arrived.', 'The girls wore gloves.'],
                'Brenda and Mandu were the bravest learners in the country.',
            ),
            _oral(
                'text_to_self',
                'Name one safe action you could take if you found an injured person.',
                'I could call a trusted adult or emergency services and avoid moving the injured person unnecessarily.',
            ),
            _open(
                'summarising',
                'Write a short news lead that tells who, what and where.',
                'Two Greenway Primary friends helped an injured six-year-old boy beside a fruit tree after school.',
            ),
        ],
    },
    {
        'title': 'The Terrible Twins',
        'grade': 4,
        'focus_word': 'Calendar',
        'visual_options': 'Calendar,Clock,Map,Notebook',
        'pages': [
            _page(
                1,
                'On 1 April, twins Todd and Ted woke early for Comic Day. They were excited to wear the funniest '
                'clothes at school and make everyone laugh.',
                'g4_twins_01.png',
                'twins,April,Comic Day,excited',
            ),
            _page(
                2,
                'The brothers spent an hour getting ready. Todd used green face paint and a green hat. Ted put on '
                'a gorilla mask. They admired their costumes in the mirror.',
                'g4_twins_02.png',
                'paint,hat,gorilla,mirror',
            ),
            _page(
                3,
                'As they walked to school, people stared and dogs chased them. The twins thought the attention '
                'proved that their costumes were wonderfully funny.',
                'g4_twins_03.png',
                'walked,stared,chased,attention',
            ),
            _page(
                4,
                'At school, every other learner wore an ordinary uniform. Todd and Ted checked the calendar and '
                'discovered their mistake: Comic Day was on 5 May, not 1 April.',
                'g4_twins_04.png',
                'ordinary,uniform,calendar,mistake',
            ),
            _page(
                5,
                'The twins felt embarrassed when the class laughed. Then they laughed at their own mistake and '
                'explained that it was not an April Fools\' trick after all.',
                'g4_twins_05.png',
                'embarrassed,laughed,explained,trick',
            ),
        ],
        'activities': [
            _prediction(
                'After people stare at the costumes, what might the twins discover at school?',
                'They might discover that something is wrong because nobody else appears to be dressed for Comic Day.',
            ),
            _choice(
                'literal_comprehension',
                'When was Comic Day actually planned?',
                ['5 May', '1 April', '5 April', '1 May'],
                '5 May',
            ),
            _choice(
                'vocabulary_in_context',
                'What does embarrassed mean in this story?',
                ['Uncomfortable because others noticed a mistake', 'Proud of winning a prize', 'Angry about missing breakfast', 'Tired after a long lesson'],
                'Uncomfortable because others noticed a mistake',
            ),
            _sequence(
                'Put the twins\' comic mistake in order.',
                [
                    'The twins dress in costumes.',
                    'People stare on the way to school.',
                    'They see learners in ordinary uniforms.',
                    'They check the date and laugh at the mistake.',
                ],
            ),
            _reasoning(
                'inference',
                'Why did the twins first think the staring was a good sign?',
                'They expected funny costumes to attract attention, so they believed their plan was working.',
            ),
            _oral(
                'text_to_self',
                'What could you do after making an embarrassing mistake?',
                'I could admit the mistake, correct it if possible and avoid being unkind to myself.',
            ),
            _open(
                'summarising',
                'Retell the mistake and resolution in two or three sentences.',
                'Todd and Ted dressed for Comic Day on the wrong date. They felt embarrassed at school but then laughed at the harmless mistake.',
            ),
        ],
    },
    {
        'title': "Frog and Crow's Wrong Message",
        'grade': 4,
        'focus_word': 'Message',
        'visual_options': 'Message,Map,Ticket,Photograph',
        'pages': [
            _page(
                1,
                'Crow sat in a marula tree when a scrap of paper blew past. He caught it and read the short '
                'message: "DM - BW - 2." Crow decided that it must be secret.',
                'g4_message_01.png',
                'marula,scrap,message,secret',
            ),
            _page(
                2,
                'Frog hopped over and helped Crow guess the meaning. Crow said DM meant "Don\'t Move" and BW '
                'meant "Beware." Frog decided that the number 2 meant the warning was for both of them.',
                'g4_message_02.png',
                'guess,beware,number,warning',
            ),
            _page(
                3,
                'Without checking their ideas, Frog and Crow imagined terrible danger. They dropped to the ground, '
                'held their heads and moaned beside the mysterious note.',
                'g4_message_03.png',
                'checking,imagined,danger,mysterious',
            ),
            _page(
                4,
                'Mrs Hen came along with a shopping basket and recognised the paper. It was her second shopping '
                'list, not a warning. She explained that DM meant dried mealies and BW meant bag of worms.',
                'g4_message_04.png',
                'basket,recognised,list,mealies',
            ),
            _page(
                5,
                'Frog and Crow laughed with relief when they understood their mistake. They had created a frightening '
                'story from an unclear message instead of asking for more information.',
                'g4_message_05.png',
                'relief,understood,unclear,information',
            ),
        ],
        'activities': [
            _choice(
                'literal_comprehension',
                'Whose paper did Crow find?',
                ['Mrs Hen\'s', 'Frog\'s', 'A teacher\'s', 'A shopkeeper\'s'],
                'Mrs Hen\'s',
            ),
            _choice(
                'vocabulary_in_context',
                'What does beware mean?',
                ['Be careful', 'Speak loudly', 'Buy food', 'Stand still'],
                'Be careful',
            ),
            _sequence(
                'Arrange the misunderstanding from beginning to end.',
                [
                    'Crow catches a scrap of paper.',
                    'Frog and Crow invent a warning.',
                    'Mrs Hen recognises her shopping list.',
                    'The friends laugh with relief.',
                ],
            ),
            _reasoning(
                'inference',
                'What caused Frog and Crow\'s fear?',
                'They guessed at the abbreviations and treated their guesses as facts without checking.',
            ),
            _choice(
                'fact_vs_opinion',
                'Which statement is supported by the story?',
                ['The note was a shopping list.', 'Crow is wiser than every animal.', 'Worms are the best food.', 'The message was written to frighten Frog.'],
                'The note was a shopping list.',
            ),
            _reasoning(
                'character_motivation',
                'Why did Mrs Hen take the paper?',
                'She recognised it as the shopping list she had lost and needed it for her shopping.',
            ),
            _open(
                'summarising',
                'Summarise the misunderstanding and its lesson.',
                'Frog and Crow misread Mrs Hen\'s shopping list as a warning and learned to check unclear information before reacting.',
            ),
        ],
    },
]
