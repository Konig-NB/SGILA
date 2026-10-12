import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from api.models import (
    Lesson, ReadingActivity, ComprehensionQuestion, 
    SequencingActivity, SpellingActivity, VisualActivityItem
)

# ============================================================
# Spring Day Surprise
# ============================================================
lesson = Lesson.objects.get(title="Spring Day Surprise")

# 1. Comprehension Questions (5)
comprehension_data = [
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
]

for cq in comprehension_data:
    ComprehensionQuestion.objects.create(lesson=lesson, **cq)
print(f"Created {len(comprehension_data)} comprehension questions for Spring Day Surprise")

# 2. Match It! (4 pairs + 1 decoy)
ReadingActivity.objects.create(
    lesson=lesson,
    activity_type=ReadingActivity.MATCHING,
    skill='literal_comprehension',
    question="Match each time to what happened.",
    options={
        "Morning": ["Saw butterflies and a nest", "Teacher announced Spring Day", "The girls played and forgot the game", "Heard giggling", "The boys splashed the girls with water"],
        "At school": ["Saw butterflies and a nest", "Teacher announced Spring Day", "The girls played and forgot the game", "Heard giggling", "The boys splashed the girls with water"],
        "After school": ["Saw butterflies and a nest", "Teacher announced Spring Day", "The girls played and forgot the game", "Heard giggling", "The boys splashed the girls with water"],
        "Near home": ["Saw butterflies and a nest", "Teacher announced Spring Day", "The girls played and forgot the game", "Heard giggling", "The boys splashed the girls with water"],
    },
    correct_answer="Morning: Saw butterflies and a nest; At school: Teacher announced Spring Day; After school: The girls played and forgot the game; Near home: Heard giggling",
    order=1,
    group_number=1,
    group_title="Match It!",
)
print("Created Match It! activity for Spring Day Surprise")

# 3. Story Sequencer (5)
SequencingActivity.objects.create(
    lesson=lesson,
    instruction="Put these events in order.",
    ordered_events=(
        "Morning: the girls walk to school and see butterflies|"
        "At school: the teacher announces Spring Day|"
        "After school: the girls play outside|"
        "Katekani remembers the water game and hurries home|"
        "Near home: the boys splash the girls with water"
    ),
)
print("Created Story Sequencer for Spring Day Surprise")

# 4. Visual Matching (5)
visual_items = [
    {'correct_word': 'butterfly', 'word_options': 'butterfly,bee,bird,ball'},
    {'correct_word': 'teacher', 'word_options': 'teacher,teach,team,tear'},
    {'correct_word': 'bucket', 'word_options': 'bucket,book,ball,bag'},
    {'correct_word': 'water', 'word_options': 'water,wait,want,walk'},
    {'correct_word': 'ball', 'word_options': 'ball,bell,bill,bull'},
]
for i, item in enumerate(visual_items):
    VisualActivityItem.objects.create(
        lesson=lesson,
        image_url=f'/static/img/g2_spring/visual_{i+1}.png',
        correct_word=item['correct_word'],
        word_options=item['word_options'],
    )
print(f"Created {len(visual_items)} visual matching items for Spring Day Surprise")

# 5. Spelling (5) - Drag Letters (unscramble)
spelling_data = [
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'B,U,T,T,E,R,F,L,Y', 'answer': 'BUTTERFLY', 'image_url': '/static/img/g2_spring/spell_butterfly.png'},
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'T,E,A,C,H,E,R', 'answer': 'TEACHER', 'image_url': '/static/img/g2_spring/spell_teacher.png'},
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'B,U,C,K,E,T', 'answer': 'BUCKET', 'image_url': '/static/img/g2_spring/spell_bucket.png'},
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'W,A,T,E,R', 'answer': 'WATER', 'image_url': '/static/img/g2_spring/spell_water.png'},
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'B,A,L,L', 'answer': 'BALL', 'image_url': '/static/img/g2_spring/spell_ball.png'},
]
for s in spelling_data:
    SpellingActivity.objects.create(lesson=lesson, **s)
print(f"Created {len(spelling_data)} spelling activities for Spring Day Surprise")

# 6. Fix the Mistake (5)
fix_mistake_data = [
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
]

for i, fm in enumerate(fix_mistake_data, 1):
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
print(f"Created {len(fix_mistake_data)} Fix the Mistake activities for Spring Day Surprise")

print("\n=== Spring Day Surprise complete ===")