import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from api.models import (
    Lesson, ReadingActivity, ComprehensionQuestion, 
    SequencingActivity, SpellingActivity, VisualActivityItem
)

# ============================================================
# Dan's Bad Week
# ============================================================
lesson = Lesson.objects.get(title="Dan's Bad Week")

# 1. Comprehension Questions (5)
comprehension_data = [
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
]

for cq in comprehension_data:
    ComprehensionQuestion.objects.create(lesson=lesson, **cq)
print(f"Created {len(comprehension_data)} comprehension questions for Dan's Bad Week")

# 2. Match It! (4 pairs + 1 decoy)
ReadingActivity.objects.create(
    lesson=lesson,
    activity_type=ReadingActivity.MATCHING,
    skill='literal_comprehension',
    question="Match each day to what happened.",
    options={
        "Monday": ["Missed the bus", "Left his bag on the bus", "Went to the wrong school", "Wore his swimming clothes", "Fell asleep in class"],
        "Tuesday": ["Missed the bus", "Left his bag on the bus", "Went to the wrong school", "Wore his swimming clothes", "Fell asleep in class"],
        "Wednesday": ["Missed the bus", "Left his bag on the bus", "Went to the wrong school", "Wore his swimming clothes", "Fell asleep in class"],
        "Thursday": ["Missed the bus", "Left his bag on the bus", "Went to the wrong school", "Wore his swimming clothes", "Fell asleep in class"],
    },
    correct_answer="Monday: Missed the bus; Tuesday: Left his bag on the bus; Wednesday: Went to the wrong school; Thursday: Wore his swimming clothes",
    order=1,
    group_number=1,
    group_title="Match It!",
)
print("Created Match It! activity for Dan's Bad Week")

# 3. Story Sequencer (5)
SequencingActivity.objects.create(
    lesson=lesson,
    instruction="Put these events in order from Monday to Friday.",
    ordered_events=(
        "Monday: Dan misses the bus|"
        "Tuesday: Dan leaves his bag on the bus|"
        "Wednesday: Dan goes to the wrong school|"
        "Thursday: Dan wears his swimming clothes|"
        "Friday: Dan falls asleep in class"
    ),
)
print("Created Story Sequencer for Dan's Bad Week")

# 4. Visual Matching (5)
visual_items = [
    {'correct_word': 'bus', 'word_options': 'bus,book,bag,ball'},
    {'correct_word': 'bag', 'word_options': 'bag,bad,big,bug'},
    {'correct_word': 'school', 'word_options': 'school,tool,pool,cool'},
    {'correct_word': 'swimming', 'word_options': 'swimming,swing,swamp,sweet'},
    {'correct_word': 'class', 'word_options': 'class,glass,grass,pass'},
]
for i, item in enumerate(visual_items):
    VisualActivityItem.objects.create(
        lesson=lesson,
        image_url=f'/static/img/g2_dan/visual_{i+1}.png',
        correct_word=item['correct_word'],
        word_options=item['word_options'],
    )
print(f"Created {len(visual_items)} visual matching items for Dan's Bad Week")

# 5. Spelling (5) - Choose the Correct Spelling
spelling_data = [
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? buss / buhs / boos / bus', 'answer': 'bus', 'image_url': '/static/img/g2_dan/spell_bus.png'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? bagg / baag / begg / bag', 'answer': 'bag', 'image_url': '/static/img/g2_dan/spell_bag.png'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? skool / schoool / scool / school', 'answer': 'school', 'image_url': '/static/img/g2_dan/spell_school.png'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? caek / kake / caik / cake', 'answer': 'cake', 'image_url': '/static/img/g2_dan/spell_cake.png'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'Which is spelled correctly? bal / baal / bahl / ball', 'answer': 'ball', 'image_url': '/static/img/g2_dan/spell_ball.png'},
]
for s in spelling_data:
    SpellingActivity.objects.create(lesson=lesson, **s)
print(f"Created {len(spelling_data)} spelling activities for Dan's Bad Week")

# 6. Fix the Mistake (5)
fix_mistake_data = [
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
print(f"Created {len(fix_mistake_data)} Fix the Mistake activities for Dan's Bad Week")

print("\n=== Dan's Bad Week complete ===")