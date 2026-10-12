import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from api.models import (
    Lesson, ReadingActivity, ComprehensionQuestion, 
    SequencingActivity, SpellingActivity, VisualActivityItem
)

# ============================================================
# A New Baby
# ============================================================
lesson = Lesson.objects.get(title="A New Baby")

# 1. Comprehension Questions (5)
comprehension_data = [
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
]

for cq in comprehension_data:
    ComprehensionQuestion.objects.create(lesson=lesson, **cq)
print(f"Created {len(comprehension_data)} comprehension questions for A New Baby")

# 2. Match It! (4 pairs + 1 decoy)
ReadingActivity.objects.create(
    lesson=lesson,
    activity_type=ReadingActivity.MATCHING,
    skill='literal_comprehension',
    question="Match each person to what they did.",
    options={
        "Bobby": ["Wanted a big brother, not a baby", "Went to hospital to have the baby", "Told Bobby the baby was a boy", "Could not play soccer yet", "Looked after Bobby while Mother was away"],
        "Mother": ["Wanted a big brother, not a baby", "Went to hospital to have the baby", "Told Bobby the baby was a boy", "Could not play soccer yet", "Looked after Bobby while Mother was away"],
        "Father": ["Wanted a big brother, not a baby", "Went to hospital to have the baby", "Told Bobby the baby was a boy", "Could not play soccer yet", "Looked after Bobby while Mother was away"],
        "Andy": ["Wanted a big brother, not a baby", "Went to hospital to have the baby", "Told Bobby the baby was a boy", "Could not play soccer yet", "Looked after Bobby while Mother was away"],
    },
    correct_answer="Bobby: Wanted a big brother, not a baby; Mother: Went to hospital to have the baby; Father: Told Bobby the baby was a boy; Andy: Could not play soccer yet",
    order=1,
    group_number=1,
    group_title="Match It!",
)
print("Created Match It! activity for A New Baby")

# 3. Story Sequencer (5)
SequencingActivity.objects.create(
    lesson=lesson,
    instruction="Put these events in order.",
    ordered_events=(
        "Mother tells Bobby about the baby|"
        "Mother goes to hospital|"
        "Father tells Bobby the baby is born|"
        "Bobby visits the hospital and meets Andy|"
        "Andy lifts his hand for a high five"
    ),
)
print("Created Story Sequencer for A New Baby")

# 4. Visual Matching (5)
visual_items = [
    {'correct_word': 'baby', 'word_options': 'baby,doctor,teacher,driver'},
    {'correct_word': 'hospital', 'word_options': 'hospital,house,home,hotel'},
    {'correct_word': 'father', 'word_options': 'father,farmer,fireman,friend'},
    {'correct_word': 'andy', 'word_options': 'andy,annie,alex,andy'},
    {'correct_word': 'hand', 'word_options': 'hand,head,heart,home'},
]
for i, item in enumerate(visual_items):
    VisualActivityItem.objects.create(
        lesson=lesson,
        image_url=f'/static/img/g2_baby/visual_{i+1}.png',
        correct_word=item['correct_word'],
        word_options=item['word_options'],
    )
print(f"Created {len(visual_items)} visual matching items for A New Baby")

# 5. Spelling (5) - Drag Letters (unscramble)
spelling_data = [
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'M,O,T,H,E,R', 'answer': 'MOTHER', 'image_url': '/static/img/g2_baby/spell_mother.png'},
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'F,A,T,H,E,R', 'answer': 'FATHER', 'image_url': '/static/img/g2_baby/spell_father.png'},
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'H,O,S,P,I,T,A,L', 'answer': 'HOSPITAL', 'image_url': '/static/img/g2_baby/spell_hospital.png'},
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'B,A,B,Y', 'answer': 'BABY', 'image_url': '/static/img/g2_baby/spell_baby.png'},
    {'activity_type': SpellingActivity.DRAG_LETTERS, 'display_text': 'H,A,N,D', 'answer': 'HAND', 'image_url': '/static/img/g2_baby/spell_hand.png'},
]
for s in spelling_data:
    SpellingActivity.objects.create(lesson=lesson, **s)
print(f"Created {len(spelling_data)} spelling activities for A New Baby")

# 6. Fix the Mistake (5)
fix_mistake_data = [
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
print(f"Created {len(fix_mistake_data)} Fix the Mistake activities for A New Baby")

print("\n=== A New Baby complete ===")