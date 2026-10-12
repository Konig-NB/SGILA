import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from api.models import (
    Lesson, ReadingActivity, ComprehensionQuestion, 
    SequencingActivity, SpellingActivity, VisualActivityItem
)

# ============================================================
# The School Shed Is on Fire
# ============================================================
lesson = Lesson.objects.get(title="The School Shed Is on Fire")

# 1. Comprehension Questions (5)
comprehension_data = [
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
]

for cq in comprehension_data:
    ComprehensionQuestion.objects.create(lesson=lesson, **cq)
print(f"Created {len(comprehension_data)} comprehension questions for The School Shed Is on Fire")

# 2. Match It! (4 pairs + 1 decoy)
ReadingActivity.objects.create(
    lesson=lesson,
    activity_type=ReadingActivity.MATCHING,
    skill='literal_comprehension',
    question="Match each person/thing to what they did.",
    options={
        "Ben the dog": ["Sniffed the smoke first", "Phoned the fire service", "Carried masks, belts and equipment", "Sprayed water on the flames", "Was saved from the fire"],
        "Teacher": ["Sniffed the smoke first", "Phoned the fire service", "Carried masks, belts and equipment", "Sprayed water on the flames", "Was saved from the fire"],
        "Firefighters": ["Sniffed the smoke first", "Phoned the fire service", "Carried masks, belts and equipment", "Sprayed water on the flames", "Was saved from the fire"],
        "Hose": ["Sniffed the smoke first", "Phoned the fire service", "Carried masks, belts and equipment", "Sprayed water on the flames", "Was saved from the fire"],
    },
    correct_answer="Ben the dog: Sniffed the smoke first; Teacher: Phoned the fire service; Firefighters: Carried masks, belts and equipment; Hose: Sprayed water on the flames",
    order=1,
    group_number=1,
    group_title="Match It!",
)
print("Created Match It! activity for The School Shed Is on Fire")

# 3. Story Sequencer (5)
SequencingActivity.objects.create(
    lesson=lesson,
    instruction="Put these events in the correct order.",
    ordered_events=(
        "The class smells smoke|"
        "Everyone stands in a line under the trees|"
        "The teacher phones the fire service|"
        "Firefighters arrive with equipment|"
        "The fire is put out and the shed is saved"
    ),
)
print("Created Story Sequencer for The School Shed Is on Fire")

# 4. Visual Matching (5)
visual_items = [
    {'correct_word': 'smoke', 'word_options': 'smoke,smell,small,smile'},
    {'correct_word': 'hose', 'word_options': 'hose,house,horse,home'},
    {'correct_word': 'teacher', 'word_options': 'teacher,teach,team,tear'},
    {'correct_word': 'bell', 'word_options': 'bell,ball,bill,belt'},
    {'correct_word': 'fire', 'word_options': 'fire,fine,firm,five'},
]
for i, item in enumerate(visual_items):
    VisualActivityItem.objects.create(
        lesson=lesson,
        image_url=f'/static/img/g2_shed/visual_{i+1}.png',
        correct_word=item['correct_word'],
        word_options=item['word_options'],
    )
print(f"Created {len(visual_items)} visual matching items for The School Shed Is on Fire")

# 5. Spelling (5) - Fill Missing Vowel
spelling_data = [
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'sm_ke', 'answer': 'smoke', 'image_url': '/static/img/g2_shed/spell_smoke.png'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'h_se', 'answer': 'hose', 'image_url': '/static/img/g2_shed/spell_hose.png'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'te_cher', 'answer': 'teacher', 'image_url': '/static/img/g2_shed/spell_teacher.png'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'b_ll', 'answer': 'bell', 'image_url': '/static/img/g2_shed/spell_bell.png'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'f_re', 'answer': 'fire', 'image_url': '/static/img/g2_shed/spell_fire.png'},
]
for s in spelling_data:
    SpellingActivity.objects.create(lesson=lesson, **s)
print(f"Created {len(spelling_data)} spelling activities for The School Shed Is on Fire")

# 6. Fix the Mistake (5)
fix_mistake_data = [
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
print(f"Created {len(fix_mistake_data)} Fix the Mistake activities for The School Shed Is on Fire")

print("\n=== The School Shed Is on Fire complete ===")