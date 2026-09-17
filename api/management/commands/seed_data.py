import random
import re

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from api.curriculum_enrichment import (
    LESSON_WORDS,
    LESSON_SPELLING,
    PRONUNCIATION_WORDS,
    STORYBOARD_PAGE_PANELS,
    VISUAL_VOCAB_SHEETS,
    build_enriched_activities,
)
from api.curriculum_library import (
    EXPANDED_STORIES,
    MANDUS_SECRET_DIARY_ACTIVITIES,
    STORYBOARD_IMAGES,
)
from api.models import (
    CauseEffectPair,
    Child,
    ComprehensionQuestion,
    FeelingsQuestion,
    InferenceQuestion,
    Lesson,
    Parent,
    PredictionQuestion,
    Progress,
    PronunciationWord,
    ReadingActivity,
    SequencingActivity,
    SpellingActivity,
    StoryPage,
    Teacher,
    TeacherClass,
    ThemeQuestion,
    VisualActivityItem,
    VocabularyQuestion,
    WrittenResponsePrompt,
)


class Command(BaseCommand):
    help = "Load clean SGILA sample data with lessons, class codes, and demo accounts"

    def handle(self, *args, **kwargs):
        Lesson.objects.all().delete()
        Child.objects.all().delete()
        Parent.objects.all().delete()
        Teacher.objects.all().delete()
        self.stdout.write('Cleared existing SGILA demo data...')

        parent = Parent.objects.create(
            full_name='Nomsa Dlamini',
            email='parent@sgila.test',
            phone='0710000000',
            password=make_password('password123'),
            accepted_popia=True,
        )
        teacher = Teacher.objects.create(
            full_name='Miss Khumalo',
            email='teacher@sgila.test',
            school_name='Thuthuka Primary',
            grades_taught='1,2,3,4',
            phone='0720000000',
            password=make_password('password123'),
            accepted_popia=True,
            class_code='SGILA1',
        )
        grade_one = TeacherClass.objects.create(
            teacher=teacher,
            name='Grade 1',
            grade=1,
            class_code='RAINB1',
        )
        TeacherClass.objects.create(
            teacher=teacher,
            name='Grade 2',
            grade=2,
            class_code='RAINB2',
        )
        TeacherClass.objects.create(
            teacher=teacher,
            name='Grade 3',
            grade=3,
            class_code='RAINB3',
        )
        TeacherClass.objects.create(
            teacher=teacher,
            name='Grade 4',
            grade=4,
            class_code='RAINB4',
        )
        child = Child.objects.create(
            parent=parent,
            teacher=teacher,
            teacher_class=grade_one,
            username='sipho_d',
            first_name='Sipho',
            last_name='Dlamini',
            name='Sipho Dlamini',
            age=7,
            grade=1,
            school_name='Thuthuka Primary',
            parent_email='learner@sgila.test',
            photo='child_photos/demo_child_photo.jpeg',
            password=make_password('password123'),
        )

        lerato_lesson = self.create_lerato_lesson()
        Progress.objects.create(
            child=child,
            lesson=lerato_lesson,
            comprehension_score=4,
            visual_score=4,
            spelling_score=4,
            total_score=12,
            total_possible=12,
            stars_earned=3,
        )
    #-------------------------------------GRADE 4 seeded_data-------------------------------------------------------------------------------------
        
        parent2 = Parent.objects.create(
            full_name='Nancy Mabunda',
            email='parent2@sgila.test',
            phone='0710000012',
            password=make_password('password123'),
            accepted_popia=True,
        )
        teacher2 = Teacher.objects.create(
            full_name='Miss Maluleke',
            email='teacher2@sgila.test',
            school_name='MK-Khambani Primary',
            grades_taught='3,4',
            phone='0720000032',
            password=make_password('password123'),
            accepted_popia=True,
            class_code='SGILA2',
        )
        grade_four = TeacherClass.objects.create(
            teacher=teacher2,
            name='Grade 4',
            grade=4,
            class_code='MKGRD4',
        )
        grade_three = TeacherClass.objects.create(
            teacher=teacher2,
            name='Grade 3',
            grade=3,
            class_code='MKGRD3',
        )
        child = Child.objects.create(
            parent=parent2,
            teacher=teacher2,
            teacher_class=grade_four,
            username='nhlulelo_m',
            first_name='nhlulelo',
            last_name='Mabunda',
            name='Nhlulelo Mabunda',
            age=10,
            grade=4,
            school_name='MK-Khambani Primary',
            parent_email='learner2@sgila.test',
            photo='child_photos/demo_child_photo.jpeg',
            password=make_password('password123'),
        )
        Child.objects.create(
            parent=parent2,
            teacher=teacher2,
            teacher_class=grade_three,
            username='lerato_m',
            first_name='Lerato',
            last_name='Mabunda',
            name='Lerato Mabunda',
            age=9,
            grade=3,
            school_name='MK-Khambani Primary',
            parent_email='learner3@sgila.test',
            photo='child_photos/demo_child_photo.jpeg',
            password=make_password('password123'),
        )

        self.create_big_book_lessons()

        self.stdout.write(self.style.SUCCESS(
            "Demo data loaded. Learner logins: sipho_d, lerato_m, nhlulelo_m; password password123."
        ))

    def add_reading_activities(self, lesson, activities):
        for order, activity in enumerate(activities, 1):
            ReadingActivity.objects.create(lesson=lesson, order=order, **activity)

    def apply_lesson_enrichment(self, lesson):
        source_activities = [
            {
                'activity_type': activity.activity_type,
                'skill': activity.skill,
                'question': activity.question,
                'options': (
                    dict(activity.options)
                    if isinstance(activity.options, dict)
                    else list(activity.options or [])
                ),
                'correct_answer': activity.correct_answer,
                'items_in_correct_order': list(activity.items_in_correct_order or []),
                'group_number': activity.group_number,
                'group_title': activity.group_title,
            }
            for activity in lesson.reading_activities.order_by('order', 'id')
        ]
        lesson.reading_activities.all().delete()
        enriched_activities = build_enriched_activities(lesson.title, source_activities)
        if lesson.grade == 3:
            lesson.sequencing_activities.all().delete()
            enriched_activities = [
                activity
                for activity in enriched_activities
                if activity.get('activity_type') not in {
                    ReadingActivity.SEQUENCING,
                    ReadingActivity.TRUE_FALSE,
                }
            ]
            selected_activities = []
            selected_skills = set()
            for activity in enriched_activities:
                skill = activity.get('skill')
                if skill not in selected_skills:
                    selected_activities.append(activity)
                    selected_skills.add(skill)
                if len(selected_activities) == 5:
                    break
            enriched_activities = selected_activities
            group_numbers = {}
            for activity in enriched_activities:
                original_group = activity.get('group_number') or 0
                if original_group:
                    if original_group not in group_numbers:
                        group_numbers[original_group] = len(group_numbers) + 1
                    activity['group_number'] = group_numbers[original_group]
        self.add_reading_activities(
            lesson,
            enriched_activities,
        )

        storyboard = STORYBOARD_IMAGES.get(lesson.title)
        panel_sequence = STORYBOARD_PAGE_PANELS.get(lesson.title)
        storyboard_url = ''
        if storyboard and panel_sequence:
            storyboard_url = f'/static/img/storyboards/{storyboard[0]}'
            pages = list(lesson.pages.order_by('page_number'))
            if len(pages) != len(panel_sequence):
                raise ValueError(
                    f'{lesson.title} has {len(pages)} pages but '
                    f'{len(panel_sequence)} storyboard panels were configured.'
                )
            for page, panel in zip(pages, panel_sequence):
                page.image_url = f'{storyboard_url}#panel-{panel}'
                page.save(update_fields=['image_url'])
            lesson.thumbnail_image = storyboard_url
            lesson.save(update_fields=['thumbnail_image'])

        lesson.visual_items.all().delete()
        lesson.pronunciation_words.all().delete()
        lesson.spelling_activities.all().delete()
        lesson_words = LESSON_WORDS.get(lesson.title)
        pronunciation_words = PRONUNCIATION_WORDS.get(lesson.title, lesson_words)
        vocab_sheet = VISUAL_VOCAB_SHEETS.get(lesson.title)
        if not lesson_words or len(lesson_words) < 5:
            raise ValueError(f'{lesson.title} must have at least five lesson words.')

        if lesson.grade != 3:
            english_words = [word for word, _isizulu, _image in lesson_words]
            for word, isizulu_word, image_source in lesson_words:
                image_url = (
                    f'/static/img/vocab_sheets/{vocab_sheet}#panel-{image_source}'
                    if isinstance(image_source, int)
                    else image_source
                )
                options = english_words.copy()
                random.Random(f'{lesson.title}:{word}').shuffle(options)
                VisualActivityItem.objects.create(
                    lesson=lesson,
                    image_url=image_url,
                    correct_word=word,
                    word_options=','.join(options),
                )
        for word, isizulu_word, image_source in pronunciation_words:
            image_url = (
                f'/static/img/vocab_sheets/{vocab_sheet}#panel-{image_source}'
                if isinstance(image_source, int)
                else image_source
            )
            audio_slug = re.sub(r'[^a-z0-9]+', '-', word.lower()).strip('-')
            PronunciationWord.objects.create(
                lesson=lesson,
                word=word,
                image_url=image_url,
                english_audio=f'voiceover:{audio_slug}-english',
                isizulu_audio=f'voiceover:{audio_slug}-zulu',
                isizulu_word=isizulu_word,
            )

        if lesson.grade != 3:
            return

        spelling_words = list(LESSON_SPELLING.get(lesson.title, []))
        existing_answers = {answer.lower() for _display_text, answer in spelling_words}
        for word, _isizulu_word, _image_source in lesson_words:
            if len(spelling_words) >= 5:
                break
            if word.lower() in existing_answers:
                continue
            display_text = word
            for vowel in 'aeiouAEIOU':
                if vowel in display_text:
                    display_text = display_text.replace(vowel, '_', 1)
                    break
            spelling_words.append((display_text, word))
            existing_answers.add(word.lower())

        if spelling_words:
            for display_text, answer in spelling_words[:5]:
                SpellingActivity.objects.create(
                    lesson=lesson,
                    activity_type=SpellingActivity.FILL_VOWEL,
                    display_text=display_text,
                    answer=answer,
                )

    def create_lerato_lesson(self):
        lesson = Lesson.objects.create(
            title="Lerato's Fruit Basket",
            grade=1,
            thumbnail_image='/static/img/lerato/Fruits.avif',
        )

        pages = [
            (
                1,
                'Lerato has a basket of fruit at home. She has a red apple, a yellow banana, and a sweet orange.',
                '/static/img/lerato/lerato_basket.png',
                'apple,banana,orange',
            ),
            (
                2,
                'Her mother bought a juicy mango from the market. Lerato puts the mango in the basket.',
                '/static/img/lerato/lerato_market.png',
                'mango,market,basket',
            ),
            (
                3,
                'Lerato eats fruit every day to stay healthy and strong.',
                '/static/img/lerato/lerato_eating.png',
                'fruit,healthy,strong',
            ),
        ]
        for page_number, text, image_url, highlighted_words in pages:
            StoryPage.objects.create(
                lesson=lesson,
                page_number=page_number,
                text=text,
                image_url=image_url,
                audio_url=f'voiceover:lerato-page-{page_number}',
                highlighted_words=highlighted_words,
            )

        questions = [
            ('What fruit is red?', 'Banana', 'Apple', 'Mango', 'Orange', 'Apple'),
            ('Which fruit is yellow?', 'Apple', 'Orange', 'Banana', 'Mango', 'Banana'),
            ('Where did the mango come from?', 'The garden', 'The market', 'The shop', 'The school', 'The market'),
            ('Why does Lerato eat fruit?', 'To stay healthy and strong', 'To hide it', 'To paint it', 'To throw it', 'To stay healthy and strong'),
        ]
        for question, option_1, option_2, option_3, option_4, answer in questions:
            ComprehensionQuestion.objects.create(
                lesson=lesson,
                question=question,
                option_1=option_1,
                option_2=option_2,
                option_3=option_3,
                option_4=option_4,
                correct_answer=answer,
            )

        self.add_reading_activities(lesson, [
            {
                'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                'skill': 'literal_comprehension',
                'question': 'What did Mother buy?',
                'options': ['A mango', 'A basket', 'A banana'],
                'correct_answer': 'A mango',
            },
            {
                'activity_type': ReadingActivity.ORAL_RESPONSE,
                'skill': 'literal_comprehension',
                'question': 'Why does Lerato eat fruit?',
                'correct_answer': 'She eats fruit to stay healthy and strong.',
            },
            {
                'activity_type': ReadingActivity.SEQUENCING,
                'skill': 'sequencing',
                'question': 'Put the story in order.',
                'items_in_correct_order': [
                    'Mother buys a mango.',
                    'Lerato puts it in the basket.',
                    'Lerato eats fruit to stay strong.',
                ],
            },
            {
                'activity_type': ReadingActivity.TRUE_FALSE,
                'skill': 'literal_comprehension',
                'question': 'Lerato keeps fruit in a basket.',
                'correct_answer': 'True',
            },
        ])

        fruit_words = [
            ('Apple', 'apple', 'Ihhabhula', '/static/img/lerato/fruit_apple.png'),
            ('Banana', 'banana', 'Ubhanana', '/static/img/lerato/fruit_banana.png'),
            ('Orange', 'orange', 'I-Oranje', '/static/img/lerato/fruit_orange_user.webp'),
            ('Mango', 'mango', 'Umango', '/static/img/lerato/fruit_mango_user.webp'),
        ]
        for word, slug, isizulu, image_url in fruit_words:
            PronunciationWord.objects.create(
                lesson=lesson,
                word=word,
                image_url=image_url,
                english_audio=f'voiceover:{slug}-english',
                isizulu_audio=f'voiceover:{slug}-zulu',
                isizulu_word=isizulu,
            )

        for image_url, correct, options in [
            ('/static/img/lerato/fruit_apple.png', 'Apple', 'Banana,Orange,Apple,Mango'),
            ('/static/img/lerato/fruit_banana.png', 'Banana', 'Apple,Mango,Orange,Banana'),
            ('/static/img/lerato/fruit_orange_user.webp', 'Orange', 'Mango,Banana,Apple,Orange'),
            ('/static/img/lerato/fruit_mango_user.webp', 'Mango', 'Orange,Apple,Mango,Banana'),
        ]:
            VisualActivityItem.objects.create(
                lesson=lesson,
                image_url=image_url,
                correct_word=correct,
                word_options=options,
            )

        SpellingActivity.objects.create(lesson=lesson, activity_type=SpellingActivity.FILL_VOWEL, display_text='B_nana', answer='Banana')
        SpellingActivity.objects.create(lesson=lesson, activity_type=SpellingActivity.FILL_VOWEL, display_text='Appl_', answer='Apple')
        SpellingActivity.objects.create(lesson=lesson, activity_type=SpellingActivity.DRAG_LETTERS, display_text='R,A,N,O,G,E', answer='ORANGE')
        SpellingActivity.objects.create(lesson=lesson, activity_type=SpellingActivity.COPY_WRITING, display_text='I eat an apple.', answer='I eat an apple.')
        self.apply_lesson_enrichment(lesson)
        return lesson

    
    
    def create_water_stopped_lesson(self):
        """Grade 4 story: The Day the Water Stopped — with all 8 specified activity types."""
        lesson = Lesson.objects.create(
            title='The Day the Water Stopped',
            grade=4,
            thumbnail_image='/static/img/water_stopped/Naledi_thumbnail.png',
        )

        # ── Story pages ───────────────────────────────────────────────────────
        pages = [
            (
                1,
                (
                    'It was a hot Tuesday afternoon in Naledi Village. The sun shone brightly, '
                    'and the dusty road outside the houses looked almost white in the heat. '
                    'After school, Amahle hurried home with her younger brother, Sizwe. '
                    'All she could think about was a cold cup of water.'
                ),
                '/static/img/water_stopped/scene1.png',
                'hurried,dusty,brightly',
            ),
            (
                2,
                (
                    'As soon as they reached the yard, Sizwe ran to the tap and turned on the tap. '
                    'Nothing came out. "Gogo!" he shouted. "The water is gone!" '
                    'Their grandmother checked the tap, but still nothing happened. '
                    'Amahle felt worried. They needed water for drinking, cooking, and washing.'
                ),
                '/static/img/water_stopped/scene2.png',
                'worried,tap,grandmother',
            ),
            (
                3,
                (
                    'Gogo sighed. "There must be a problem with the main pipe again. '
                    'We must use what we have very carefully." '
                    'Amahle looked at the little water left in the bucket. '
                    '"This won\'t last until tomorrow," she said. '
                    'Just then, Amahle remembered the big rain tank behind the community hall.'
                ),
                '/static/img/water_stopped/scene3.png',
                'carefully,bucket,community',
            ),
            (
                4,
                (
                    '"Gogo, maybe we can fetch water from the tank," she said. '
                    'Gogo nodded. "Take the small containers. They will be easier to carry." '
                    'Along the way, they passed their neighbour, Mr Dlamini. '
                    'He brought them an old blue wheelbarrow with one squeaky wheel to carry the containers.'
                ),
                '/static/img/water_stopped/scene4.png',
                'containers,neighbour,wheelbarrow',
            ),
            (
                5,
                (
                    'When they reached the community hall, they were relieved to hear dripping water. '
                    'A few people from the village were already there, filling buckets and bottles. '
                    'Everyone looked tired, but they greeted one another kindly. '
                    'Amahle and Sizwe filled their containers one by one.'
                ),
                '/static/img/water_stopped/scene5.png',
                'relieved,village,greeted',
            ),
            (
                6,
                (
                    'As they rested on the way home, Amahle noticed an elderly woman struggling with a large bucket. '
                    'Without waiting, she walked over to help. '
                    '"Kindness returns to those who share it," the woman said with a smile. '
                    'By the time they got home, Gogo smiled proudly. '
                    'Amahle had learned that water was precious and people must work together when it is scarce.'
                ),
                '/static/img/water_stopped/scene6.png',
                'struggling,precious,scarce',
            ),
        ]
        for page_number, text, image_url, highlighted_words in pages:
            StoryPage.objects.create(
                lesson=lesson,
                page_number=page_number,
                text=text,
                image_url=image_url,
                audio_url=f'voiceover:water-page-{page_number}',
                highlighted_words=highlighted_words,
            )

        # ── ACTIVITY TYPE 1: Vocabulary — Match the word to the meaning ───────
        VocabularyQuestion.objects.create(
            lesson=lesson,
            word='hurried',
            option_1='moved quickly',
            option_2='slept deeply',
            option_3='spoke softly',
            correct_answer='moved quickly',
        )
        VocabularyQuestion.objects.create(
            lesson=lesson,
            word='relieved',
            option_1='angry and upset',
            option_2='happy because a worry has ended',
            option_3='tired and bored',
            correct_answer='happy because a worry has ended',
        )
        VocabularyQuestion.objects.create(
            lesson=lesson,
            word='worried',
            option_1='feeling afraid something bad might happen',
            option_2='feeling happy and excited',
            option_3='feeling sleepy and bored',
            correct_answer='feeling afraid something bad might happen',
        )
        VocabularyQuestion.objects.create(
            lesson=lesson,
            word='precious',
            option_1='very heavy and hard to carry',
            option_2='very valuable and important',
            option_3='very old and broken',
            correct_answer='very valuable and important',
        )
        VocabularyQuestion.objects.create(
            lesson=lesson,
            word='scarce',
            option_1='not enough of something',
            option_2='too much of something',
            option_3='easy to find everywhere',
            correct_answer='not enough of something',
        )
        VocabularyQuestion.objects.create(
            lesson=lesson,
            word='struggling',
            option_1='moving very fast',
            option_2='working very hard against something difficult',
            option_3='laughing at something funny',
            correct_answer='working very hard against something difficult',
        )

        # ── ACTIVITY 1: Basic Comprehension Questions ─────────────────────────
        comprehension_questions = [
            (
                'Why did Amahle hurry home after school?',
                'She wanted to play outside',
                'She wanted a cold cup of water',
                'She was late for school',
                'She wanted to visit Mr Dlamini',
                'She wanted a cold cup of water',
            ),
            (
                'What problem did the family have?',
                'There was no food',
                'The rain tank was broken',
                'The tap had no water',
                'Sizwe was lost',
                'The tap had no water',
            ),
            (
                'Where did Amahle suggest they should get water?',
                'From the river',
                'From the shop',
                'From the community tank',
                'From the school',
                'From the community tank',
            ),
            (
                'How did Mr Dlamini help them?',
                'He gave them money',
                'He drove them in a car',
                'He gave them a wheelbarrow',
                'He fixed the tap',
                'He gave them a wheelbarrow',
            ),
            (
                'What lesson did Amahle learn at the end?',
                'School is difficult',
                'Water should not be wasted',
                'Children should stay indoors',
                'The road is too dusty',
                'Water should not be wasted',
            ),
        ]
        for question, o1, o2, o3, o4, answer in comprehension_questions:
            ComprehensionQuestion.objects.create(
                lesson=lesson,
                question=question,
                option_1=o1,
                option_2=o2,
                option_3=o3,
                option_4=o4,
                correct_answer=answer,
            )

        # ── ACTIVITY 2: Sequencing — Put events in the correct order ──────────
        SequencingActivity.objects.create(
            lesson=lesson,
            instruction='Put these events in the correct order.',
            ordered_events=(
                'Sizwe opened the tap, but no water came out.|'
                'Mr Dlamini brought them a wheelbarrow.|'
                'Amahle and Sizwe fetched water from the community tank.|'
                'Amahle helped an elderly woman on the way home.'
            ),
        )

        # ── ACTIVITY 3: Inference — Read between the lines ────────────────────
        inference_questions = [
            (
                'Why did Gogo tell them to take the small containers?',
                'Because the big ones were dirty',
                'Because small containers were easier to carry',
                'Because she wanted more containers left at home',
                'Because small containers hold more water',
                'Because small containers were easier to carry',
            ),
            (
                'How do you know Amahle is responsible?',
                'She ignored the problem',
                'She waited for someone else',
                'She thought of a solution and helped others',
                'She refused to carry water',
                'She thought of a solution and helped others',
            ),
            (
                'Why were people at the tank greeting one another kindly?',
                'They were all on holiday',
                'They were helping each other during a difficult time',
                'They were laughing at the problem',
                'They did not know each other',
                'They were helping each other during a difficult time',
            ),
        ]
        for question, o1, o2, o3, o4, answer in inference_questions:
            InferenceQuestion.objects.create(
                lesson=lesson,
                question=question,
                option_1=o1,
                option_2=o2,
                option_3=o3,
                option_4=o4,
                correct_answer=answer,
            )

        # ── ACTIVITY 4: Prediction — What happens next? ───────────────────────
        PredictionQuestion.objects.create(
            lesson=lesson,
            stop_point_text='"This won\'t last until tomorrow," she said.',
            question='What do you think Amahle will do next?',
            option_1='She will waste the little water that is left',
            option_2='She will think of another place to get water',
            option_3='She will go to sleep',
            option_4='She will break the tap',
            correct_answer='She will think of another place to get water',
        )

        # ── ACTIVITY 5: Feelings / Emotional Literacy ─────────────────────────
        feelings_questions = [
            (
                'How did Amahle probably feel when no water came from the tap?',
                'excited', 'worried', 'bored', 'proud',
                'worried',
            ),
            (
                'How did Amahle and Sizwe feel when they heard water dripping at the tank?',
                'relieved', 'frightened', 'angry', 'confused',
                'relieved',
            ),
            (
                'How did Gogo feel when the children came home with water?',
                'proud', 'lazy', 'cross', 'nervous',
                'proud',
            ),
        ]
        for question, o1, o2, o3, o4, answer in feelings_questions:
            FeelingsQuestion.objects.create(
                lesson=lesson,
                question=question,
                option_1=o1,
                option_2=o2,
                option_3=o3,
                option_4=o4,
                correct_answer=answer,
            )

        # ── ACTIVITY 6: Cause and Effect ─────────────────────────────────────
        cause_effect_pairs = [
            (1, 'The tap stopped working.',          'Amahle and Sizwe needed another way to get water.'),
            (2, 'Mr Dlamini brought a wheelbarrow.', 'Carrying the containers became easier.'),
            (3, 'Amahle helped the elderly woman.',  'The woman thanked Amahle.'),
            (4, 'The family used their water carefully.', 'Their small supply could last longer.'),
        ]
        for order, cause, effect in cause_effect_pairs:
            CauseEffectPair.objects.create(
                lesson=lesson,
                order=order,
                cause=cause,
                effect=effect,
            )

        # ── ACTIVITY 7: Theme / Main Lesson ───────────────────────────────────
        ThemeQuestion.objects.create(
            lesson=lesson,
            question='What is the main lesson of the story?',
            option_1='People should always stay inside when it is hot.',
            option_2='Water is precious, and communities should help one another.',
            option_3='Children should not walk on dusty roads.',
            option_4='Wheelbarrows are useful tools.',
            correct_answer='Water is precious, and communities should help one another.',
        )

        # ── ACTIVITY 8: Short Written Response ───────────────────────────────
        WrittenResponsePrompt.objects.create(
            lesson=lesson,
            prompt='What would you do if your home had no water for one day?',
            guidance='Write 3 to 4 sentences.',
        )

        self.add_reading_activities(lesson, [
            {
                'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                'skill': 'literal_comprehension',
                'question': 'What caused the family\'s main problem?',
                'options': [
                    'No water came from the tap.',
                    'The community hall was closed.',
                    'The wheelbarrow was missing.',
                    'The weather became cold.',
                ],
                'correct_answer': 'No water came from the tap.',
            },
            {
                'activity_type': ReadingActivity.CLOZE,
                'skill': 'vocabulary_in_context',
                'question': 'Water was scarce. This means there was ____.',
                'options': ['not enough water', 'clean water everywhere', 'water only at school'],
                'correct_answer': 'not enough water',
            },
            {
                'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                'skill': 'summarising',
                'question': 'Which detail is most important to the story\'s solution?',
                'options': [
                    'The wheelbarrow had one squeaky wheel.',
                    'Amahle remembered the community rain tank.',
                    'The road looked white in the heat.',
                    'The containers were filled one by one.',
                ],
                'correct_answer': 'Amahle remembered the community rain tank.',
            },
            {
                'activity_type': ReadingActivity.REASONING,
                'skill': 'inference',
                'question': 'How do Amahle\'s actions show that she is responsible? Use two story details.',
                'correct_answer': (
                    'Amahle remembered the community tank and helped fetch water. '
                    'She also helped the elderly woman carry her bucket.'
                ),
            },
            {
                'activity_type': ReadingActivity.REASONING,
                'skill': 'character_motivation',
                'question': 'How did Gogo feel when the children returned, and what proves it?',
                'correct_answer': 'Gogo felt proud because the story says that she smiled proudly.',
            },
            {
                'activity_type': ReadingActivity.PREDICTION,
                'skill': 'prediction',
                'question': 'If the tap stays dry tomorrow, what should the family do next, and why?',
                'correct_answer': (
                    'They could return to the community tank with suitable containers and keep '
                    'sharing water carefully because the story shows that the tank still has water.'
                ),
            },
            {
                'activity_type': ReadingActivity.OPEN_ENDED,
                'skill': 'summarising',
                'question': 'Summarise the problem, solution, and lesson in your own words.',
                'correct_answer': (
                    'When the taps stopped, Amahle and Sizwe fetched water from the community tank '
                    'with help from a neighbour. Amahle learned that water is precious and people '
                    'should help one another.'
                ),
            },
        ])

        self.apply_lesson_enrichment(lesson)
        return lesson

    def create_story_lesson(self, *, title, grade, pages, activities, focus_word, visual_options):
        storyboard = STORYBOARD_IMAGES.get(title)
        storyboard_url = (
            f'/static/img/storyboards/{storyboard[0]}'
            if storyboard else ''
        )
        lesson = Lesson.objects.create(
            title=title,
            grade=grade,
            thumbnail_image=storyboard_url or pages[0][2],
        )
        for page_number, text, image_url, highlighted_words in pages:
            StoryPage.objects.create(
                lesson=lesson,
                page_number=page_number,
                text=text,
                image_url=storyboard_url or image_url,
                audio_url=f'voiceover:{title.lower().replace(" ", "-")}-{page_number}',
                highlighted_words=highlighted_words,
            )

        self.add_reading_activities(lesson, activities)
        focus_image = (
            f'{storyboard_url}#panel-{storyboard[1]}'
            if storyboard else pages[0][2]
        )
        VisualActivityItem.objects.create(
            lesson=lesson,
            image_url=focus_image,
            correct_word=focus_word,
            word_options=visual_options,
        )
        PronunciationWord.objects.create(
            lesson=lesson,
            word=focus_word,
            image_url=focus_image,
            english_audio=f'voiceover:{focus_word.lower()}-english',
        )
        SpellingActivity.objects.create(
            lesson=lesson,
            activity_type=SpellingActivity.COPY_WRITING,
            display_text=f'I can read the word {focus_word.lower()}.',
            answer=f'I can read the word {focus_word.lower()}.',
        )
        self.apply_lesson_enrichment(lesson)
        return lesson

    def create_big_book_lessons(self):
        """Create authentic Grade 1-4 stories adapted from the supplied CAPS readers."""
        self.create_story_lesson(
            title='A Very Hot Day',
            grade=1,
            focus_word='Pond',
            visual_options='Pond,School,Bus,House',
            pages=[
                (
                    1,
                    'Karabo, Tshepo and Cathy loved to play soccer. One Saturday, the day was very hot. '
                    'They played for a few minutes, but soon they were sweating. "It is too hot!" said Karabo.',
                    '/static/img/caps/g1_hot_01.png',
                    'soccer,hot,sweating',
                ),
                (
                    2,
                    'The friends stopped playing and walked home. They passed children at the park who looked hot too. '
                    'Then Karabo remembered the cool pond nearby. He had an idea.',
                    '/static/img/caps/g1_hot_02.png',
                    'stopped,park,pond',
                ),
                (
                    3,
                    'At the pond, Karabo took off his shoes and jumped into the water. "Good idea!" said Tshepo. '
                    'The cool water helped Karabo feel better.',
                    '/static/img/caps/g1_hot_03.png',
                    'shoes,jumped,cool',
                ),
                (
                    4,
                    'Cathy laughed. A little fish was resting on Karabo\'s head! Karabo laughed too. '
                    '"I could swim all day," he said.',
                    '/static/img/caps/g1_hot_04.png',
                    'fish,laughed,swim',
                ),
            ],
            activities=[
                {
                    'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                    'skill': 'literal_comprehension',
                    'question': 'Why did they stop playing?',
                    'options': ['It was too hot.', 'They lost the ball.', 'School started.'],
                    'correct_answer': 'It was too hot.',
                },
                {
                    'activity_type': ReadingActivity.ORAL_RESPONSE,
                    'skill': 'literal_comprehension',
                    'question': 'Who played soccer?',
                    'correct_answer': 'Karabo, Tshepo and Cathy played soccer.',
                },
                {
                    'activity_type': ReadingActivity.SEQUENCING,
                    'skill': 'sequencing',
                    'question': 'Put the story in order.',
                    'items_in_correct_order': [
                        'The friends play soccer.',
                        'Karabo remembers the pond.',
                        'Karabo jumps into the water.',
                    ],
                },
                {
                    'activity_type': ReadingActivity.TRUE_FALSE,
                    'skill': 'literal_comprehension',
                    'question': 'A fish sat on Karabo\'s head.',
                    'correct_answer': 'True',
                },
            ],
        )

        self.create_story_lesson(
            title="A Dog's Life",
            grade=2,
            focus_word='Dog',
            visual_options='Dog,Bus,Book,Ball',
            pages=[
                (
                    1,
                    'On Thursday, Abby and Lebo got onto the school bus. Poor Ben could not get onto the bus. '
                    '"No Ben, you cannot come on," said Lebo. "No dogs allowed!"',
                    '/static/img/caps/g2_dog_01.png',
                    'Thursday,bus,allowed',
                ),
                (
                    2,
                    'On Friday, Abby and Lebo went to the library, but Ben could not go inside. On Saturday, '
                    'they went to the beach, but Ben could not go with them.',
                    '/static/img/caps/g2_dog_02.png',
                    'Friday,library,Saturday,beach',
                ),
                (
                    3,
                    'On Sunday, Abby and Lebo went to the park. Ben sat under a tree at the gate. '
                    'He waited and waited. Then he fell asleep and began to dream.',
                    '/static/img/caps/g2_dog_03.png',
                    'Sunday,park,waited,dream',
                ),
                (
                    4,
                    'Ben dreamed that he rode on the bus and sat at the front. Then he dreamed that he sat '
                    'in class between Abby and Lebo.',
                    '/static/img/caps/g2_dog_04.png',
                    'dreamed,front,class',
                ),
                (
                    5,
                    'Ben dreamed that he dug in the sand, surfed in the waves, and played with other dogs. '
                    'He went on the swing, slide and merry-go-round.',
                    '/static/img/caps/g2_dog_05.png',
                    'sand,waves,swing,slide',
                ),
                (
                    6,
                    'Then Abby and Lebo came back. "Wake up, Ben! We are going home," said Lebo. '
                    'Ben opened his eyes and realised that his adventure had only been a dream.',
                    '/static/img/caps/g2_dog_06.png',
                    'wake,home,realised',
                ),
            ],
            activities=[
                {
                    'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                    'skill': 'literal_comprehension',
                    'question': 'Where did Ben fall asleep?',
                    'options': ['Under a tree', 'On the bus', 'In the library'],
                    'correct_answer': 'Under a tree',
                },
                {
                    'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                    'skill': 'vocabulary_in_context',
                    'question': 'What does dreamed mean in this story?',
                    'options': [
                        'Ben imagined events while asleep.',
                        'Ben remembered yesterday.',
                        'Ben planned a real trip.',
                    ],
                    'correct_answer': 'Ben imagined events while asleep.',
                },
                {
                    'activity_type': ReadingActivity.SEQUENCING,
                    'skill': 'sequencing',
                    'question': 'Put the real visits in order.',
                    'items_in_correct_order': [
                        'Abby and Lebo rode the bus.',
                        'They went to the library.',
                        'They visited the beach.',
                        'They went to the park.',
                    ],
                },
                {
                    'activity_type': ReadingActivity.REASONING,
                    'skill': 'inference',
                    'question': 'Why was Ben unhappy when he woke up?',
                    'correct_answer': 'He realised that the fun places he visited were only part of his dream.',
                },
                {
                    'activity_type': ReadingActivity.TRUE_FALSE,
                    'skill': 'literal_comprehension',
                    'question': 'Ben really rode on the school bus.',
                    'correct_answer': 'False',
                },
            ],
        )

        self.create_story_lesson(
            title='A New Baby',
            grade=2,
            focus_word='Baby',
            visual_options='Baby,Doctor,Teacher,Driver',
            pages=[
                (
                    1,
                    'Bobby\'s mother told him that she was going to have a baby. She said Granny would look '
                    'after him while she was in hospital. Bobby complained that he wanted a big brother, not a baby.',
                    '/static/img/caps/g2_baby_01.png',
                    'baby,Granny,hospital,complained',
                ),
                (
                    2,
                    'A few days later, Mother went to hospital. Father told Bobby that the baby had been born. '
                    '"Is it a girl or a boy?" Bobby asked. "It is a boy," Father answered.',
                    '/static/img/caps/g2_baby_02.png',
                    'born,boy,Father',
                ),
                (
                    3,
                    'That afternoon, Father, Bobby and Granny went to the busy hospital. Bobby saw doctors, '
                    'nurses and an ambulance before they reached the baby ward.',
                    '/static/img/caps/g2_baby_03.png',
                    'doctors,nurses,ambulance,ward',
                ),
                (
                    4,
                    'Bobby stared at a baby wearing a Bafana jersey. He knew this was his brother. '
                    '"He is so cute. He looks just like me," Bobby said.',
                    '/static/img/caps/g2_baby_04.png',
                    'jersey,brother,cute',
                ),
                (
                    5,
                    'The baby\'s name was Andy. He did not have teeth and could not play soccer yet. '
                    'Bobby looked carefully at his little brother.',
                    '/static/img/caps/g2_baby_05.png',
                    'Andy,teeth,soccer',
                ),
                (
                    6,
                    'Baby Andy opened his eyes and lifted his hand. Bobby thought Andy was giving him a high five. '
                    '"I love you just as you are. We will play soccer when you are older," Bobby said.',
                    '/static/img/caps/g2_baby_06.png',
                    'eyes,high five,older',
                ),
            ],
            activities=[
                {
                    'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                    'skill': 'literal_comprehension',
                    'question': 'Who looked after Bobby?',
                    'options': ['Granny', 'A nurse', 'His teacher'],
                    'correct_answer': 'Granny',
                },
                {
                    'activity_type': ReadingActivity.MULTIPLE_CHOICE,
                    'skill': 'vocabulary_in_context',
                    'question': 'Bobby complained. What does complained mean?',
                    'options': ['He said he was unhappy.', 'He laughed loudly.', 'He asked for help.'],
                    'correct_answer': 'He said he was unhappy.',
                },
                {
                    'activity_type': ReadingActivity.SEQUENCING,
                    'skill': 'sequencing',
                    'question': 'Put these events in order.',
                    'items_in_correct_order': [
                        'Mother tells Bobby about the baby.',
                        'Father says the baby is born.',
                        'The family visits the hospital.',
                        'Bobby welcomes baby Andy.',
                    ],
                },
                {
                    'activity_type': ReadingActivity.REASONING,
                    'skill': 'inference',
                    'question': 'Why could Andy not play soccer yet?',
                    'correct_answer': 'Andy was a newborn baby and was too young to play soccer.',
                },
                {
                    'activity_type': ReadingActivity.REASONING,
                    'skill': 'character_motivation',
                    'question': 'Why did Bobby change his mind about the baby?',
                    'correct_answer': 'When Bobby met Andy, he thought the baby was cute and began to love him.',
                },
            ],
        )

        self.create_story_lesson(
            title="Mandu's Secret Diary",
            grade=3,
            focus_word='Diary',
            visual_options='Diary,Newspaper,Map,Poster',
            pages=[
                (
                    1,
                    'Mandu wrote in her diary every day. She recorded what she did and wrote secrets that she '
                    'did not want anyone else to see.',
                    '/static/img/caps/g3_mandu_01.png',
                    'diary,recorded,secrets',
                ),
                (
                    2,
                    'Mandu needed a good hiding place, so she put the diary under her bed. One afternoon, Mandu '
                    'and her friend Anna came home and found the diary lying open on the bedroom floor.',
                    '/static/img/caps/g3_mandu_02.png',
                    'hiding,under,open',
                ),
                (
                    3,
                    'Anna noticed dirty fingerprints on the diary. Mandu suspected her younger brother, Thabo, '
                    'because his fingers were often dirty. Then she remembered that he was only five and could not read.',
                    '/static/img/caps/g3_mandu_03.png',
                    'fingerprints,suspected,read',
                ),
                (
                    4,
                    'Mandu found a blond hair between the pages. Everyone in her family had black hair. '
                    'She looked suspiciously at Anna\'s blond hair.',
                    '/static/img/caps/g3_mandu_04.png',
                    'blond,clue,suspiciously',
                ),
                (
                    5,
                    'The girls set a trap. Mandu put the diary under the bed and sprinkled flour on the floor. '
                    'They hid around the corner and waited. Soon they heard scratching in the bedroom.',
                    '/static/img/caps/g3_mandu_05.png',
                    'trap,flour,scratching',
                ),
                (
                    6,
                    'They ran into the room and saw floury paw prints. Zola, Mandu\'s long-haired blond dog, '
                    'was playing with the diary. They had found the culprit at last. Mandu felt relieved and '
                    'amused. Anna laughed and told Mandu to find a much better hiding place for her diary.',
                    '/static/img/caps/g3_mandu_06.png',
                    'paw prints,Zola,culprit',
                ),
            ],
            activities=MANDUS_SECRET_DIARY_ACTIVITIES,
        )

        for story in EXPANDED_STORIES:
            self.create_story_lesson(**story)
