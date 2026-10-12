import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sgila_project.settings')
django.setup()

from api.models import (
    Lesson, ReadingActivity, ComprehensionQuestion, 
    SequencingActivity, SpellingActivity, VisualActivityItem
)

# ============================================================
# A Dog's Life
# ============================================================
lesson = Lesson.objects.get(title="A Dog's Life")

# 1. Comprehension Questions (5)
comprehension_data = [
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
]

for cq in comprehension_data:
    ComprehensionQuestion.objects.create(lesson=lesson, **cq)
print(f"Created {len(comprehension_data)} comprehension questions for A Dog's Life")

# 2. Match It! (4 pairs + 1 decoy) - stored as ReadingActivity with matching type
ReadingActivity.objects.create(
    lesson=lesson,
    activity_type=ReadingActivity.MATCHING,
    skill='literal_comprehension',
    question="Match each place to what happened there.",
    options={
        "Bus": ["No dogs allowed", "Ben could not go with them", "Ben waited under a tree", "Ben surfed in the waves", "Ben could not go inside"],
        "Beach": ["No dogs allowed", "Ben could not go with them", "Ben waited under a tree", "Ben surfed in the waves", "Ben could not go inside"],
        "Park": ["No dogs allowed", "Ben could not go with them", "Ben waited under a tree", "Ben surfed in the waves", "Ben could not go inside"],
        "Dream": ["No dogs allowed", "Ben could not go with them", "Ben waited under a tree", "Ben surfed in the waves", "Ben could not go inside"],
    },
    correct_answer="Bus: No dogs allowed; Beach: Ben could not go with them; Park: Ben waited under a tree; Dream: Ben surfed in the waves",
    order=1,
    group_number=1,
    group_title="Match It!",
)
print("Created Match It! activity for A Dog's Life")

# 3. Story Sequencer (5)
SequencingActivity.objects.create(
    lesson=lesson,
    instruction="Put these events in the correct order.",
    ordered_events=(
        "Ben is not allowed on the bus|"
        "Ben is not allowed at the library or beach|"
        "Ben waits under the tree at the park|"
        "Ben falls asleep and dreams of an adventure|"
        "Abby and Lebo wake Ben up"
    ),
)
print("Created Story Sequencer for A Dog's Life")

# 4. Visual Matching (5) - need image URLs
visual_items = [
    {'correct_word': 'bus', 'word_options': 'bus,book,ball,bag'},
    {'correct_word': 'beach', 'word_options': 'beach,bench,book,bus'},
    {'correct_word': 'tree', 'word_options': 'tree,train,truck,book'},
    {'correct_word': 'wave', 'word_options': 'wave,wall,water,wind'},
    {'correct_word': 'dream', 'word_options': 'dream,drink,dress,draw'},
]
# Note: Image URLs would need to be provided - using placeholders
for i, item in enumerate(visual_items):
    VisualActivityItem.objects.create(
        lesson=lesson,
        image_url=f'/static/img/g2_dog/visual_{i+1}.png',
        correct_word=item['correct_word'],
        word_options=item['word_options'],
    )
print(f"Created {len(visual_items)} visual matching items for A Dog's Life")

# 5. Spelling (5) - Fill Missing Vowel
spelling_data = [
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'b_s', 'answer': 'bus'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'b_ok', 'answer': 'book'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'tr_e', 'answer': 'tree'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'cl_ud', 'answer': 'cloud'},
    {'activity_type': SpellingActivity.FILL_VOWEL, 'display_text': 'w_ve', 'answer': 'wave'},
]
for s in spelling_data:
    SpellingActivity.objects.create(lesson=lesson, **s)
print(f"Created {len(spelling_data)} spelling activities for A Dog's Life")

# 6. Fix the Mistake (5) - stored as ReadingActivity with cloze type
fix_mistake_data = [
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
print(f"Created {len(fix_mistake_data)} Fix the Mistake activities for A Dog's Life")

print("\n=== A Dog's Life complete ===")