from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

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
            grades_taught='1,2',
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

        self.create_water_stopped_lesson()
        self.create_extra_lessons()

        self.stdout.write(self.style.SUCCESS(
            "Demo data loaded. Logins: learner@sgila.test / parent@sgila.test / teacher@sgila.test, password password123. Class code RAINB1."
        ))

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
                'The tap worked again the next morning.'
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
                'How did Sizwe feel when the tap worked again?',
                'cheerful', 'frightened', 'angry', 'confused',
                'cheerful',
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
            (4, 'The tap worked again the next morning.', 'The family could use water from the sink again.'),
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

        return lesson

    def create_extra_lessons(self):
        extra_lessons = [
            (2, 'Lebo and the Lion', 'lion'),
            (2, 'The Big River', 'river'),
            (3, 'Grandma Finds a Map', 'map'),
        ]
        for grade, title, word in extra_lessons:
            extra = Lesson.objects.create(
                title=title,
                grade=grade,
                thumbnail_image=f'/images/{word}.png',
            )
            StoryPage.objects.create(
                lesson=extra, page_number=1,
                text=f'{title} is a short SGILA practice story. Read slowly and look for the word {word}.',
                image_url=f'/images/{word}.png',
                audio_url=f'/audio/story/{word}.mp3',
                highlighted_words=word,
            )
            ComprehensionQuestion.objects.create(
                lesson=extra, question='What should you do first?',
                option_1='Read carefully', option_2='Close the app',
                option_3='Skip the story', option_4='Guess quickly',
                correct_answer='Read carefully',
            )
            VisualActivityItem.objects.create(
                lesson=extra, image_url=f'/images/{word}.png',
                correct_word=word.title(),
                word_options=f'{word.title()},Apple,Banana,Book',
            )
            PronunciationWord.objects.create(
                lesson=extra, word=word.title(),
                image_url=f'/images/{word}.png',
                english_audio=f'/audio/pronunciation/{word}.mp3',
                isizulu_word='',
            )
            SpellingActivity.objects.create(
                lesson=extra, activity_type=SpellingActivity.COPY_WRITING,
                display_text=f'I can read {word}.',
                answer=f'I can read {word}.',
            )
