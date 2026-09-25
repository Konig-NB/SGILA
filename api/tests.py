import json
import re
from unittest.mock import patch
from pathlib import Path

from django.contrib.auth.hashers import make_password
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from api.curriculum_enrichment import (
    EXTRA_ACTIVITIES,
    LESSON_COVERS,
    LESSON_WORDS,
    LESSON_SPELLING,
    PRONUNCIATION_WORDS,
    STORYBOARD_PAGE_PANELS,
    VISUAL_VOCAB_SHEETS,
)
from api.curriculum_library import STORYBOARD_IMAGES
from api.models import (
    AccountActionOTP,
    Child,
    ComprehensionQuestion,
    GradeHistory,
    Lesson,
    OTPToken,
    Parent,
    PronunciationWord,
    Progress,
    ReadingActivity,
    ReadingActivityResponse,
    SpellingActivity,
    StoryPage,
    Subscription,
    Teacher,
    TeacherClass,
    VisualActivityItem,
    current_school_year,
)


class SgilaFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.lesson = Lesson.objects.create(title="Market Practice", grade=1)
        StoryPage.objects.create(
            lesson=self.lesson,
            page_number=1,
            text="Sipho reads at the market.",
            highlighted_words="Sipho,market",
        )
        ComprehensionQuestion.objects.create(
            lesson=self.lesson,
            question="Where is Sipho?",
            option_1="Market",
            option_2="School",
            option_3="River",
            option_4="Home",
            correct_answer="Market",
        )
        self.reading_activity = ReadingActivity.objects.create(
            lesson=self.lesson,
            order=1,
            activity_type=ReadingActivity.MULTIPLE_CHOICE,
            skill='literal_comprehension',
            question='Where is Sipho?',
            options=['Market', 'School', 'River'],
            correct_answer='Market',
        )
        VisualActivityItem.objects.create(
            lesson=self.lesson,
            correct_word="Market",
            word_options="Market,School,River,Home",
        )
        PronunciationWord.objects.create(lesson=self.lesson, word="Market")
        SpellingActivity.objects.create(
            lesson=self.lesson,
            activity_type=SpellingActivity.COPY_WRITING,
            display_text="I can read.",
            answer="I can read.",
        )

    def sign_in_child(self, child):
        session = self.client.session
        session['account_role'] = 'learner'
        session['account_id'] = child.id
        session['account_name'] = child.name
        session['child_id'] = child.id
        session['child_name'] = child.name
        session['child_grade'] = child.grade
        session.save()

    def test_terrible_twins_extra_activity_is_marked_as_comprehension(self):
        self.assertEqual(
            EXTRA_ACTIVITIES['The Terrible Twins']['skill'],
            'literal_comprehension',
        )

    def test_frontend_has_one_layered_stylesheet_without_force_overrides(self):
        project_root = Path(__file__).resolve().parent.parent
        stylesheet = project_root / 'static' / 'css' / 'sgila_app.css'
        css = stylesheet.read_text(encoding='utf-8')

        self.assertTrue(stylesheet.is_file())
        self.assertIn('@layer foundation, application, pages;', css)
        self.assertNotIn('!important', css)
        self.assertEqual(css.count('{'), css.count('}'))
        self.assertIn(
            '[data-theme="dark"] img {\n  opacity: .95;\n}\n\n/* Reading Studio homepage */',
            css,
        )
        self.assertFalse((stylesheet.parent / 'sgila.css').exists())
        self.assertFalse((stylesheet.parent / 'sgila_web.css').exists())

        for template in (project_root / 'templates').glob('*.html'):
            with self.subTest(template=template.name):
                template_html = template.read_text(encoding='utf-8')
                self.assertNotIn('<style>', template_html)
                inline_styles = re.findall(r'style="([^"]*)"', template_html)
                self.assertTrue(all(
                    style.strip().startswith('--progress:')
                    for style in inline_styles
                ))
                self.assertNotRegex(
                    template_html,
                    r'\.style\.(display|width|color|margin|padding|background|border)\s*=',
                )

        response = self.client.get('/login?role=learner')
        self.assertContains(response, 'css/sgila_app.css')
        self.assertNotContains(response, 'css/sgila.css')
        self.assertNotContains(response, 'css/sgila_web.css')

    def test_learner_can_reach_lesson_flow(self):
        child = Child.objects.create(
            username="sipho",
            name="Sipho",
            age=7,
            grade=1,
            school_name="Thuthuka Primary",
            parent_email="sipho@example.com",
            password=make_password("password123"),
        )
        session = self.client.session
        session.update({
            'account_role': 'learner',
            'account_id': child.id,
            'account_name': child.name,
            'child_id': child.id,
            'child_name': child.name,
            'child_grade': child.grade,
        })
        session.save()

        for path in [
            f"/lessons/{self.lesson.id}/story",
            f"/lessons/{self.lesson.id}/questions",
            f"/lessons/{self.lesson.id}/visual-activity",
            f"/lessons/{self.lesson.id}/pronunciation",
            f"/lessons/{self.lesson.id}/spelling",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_parent_and_teacher_registration_routes_to_dashboards(self):
        parent_response = self.client.post("/register", {
            "role": "parent",
            "full_name": "Nomsa Dlamini",
            "email": "nomsa@example.com",
            "phone": "0710000000",
            "password": "password123",
            "accepted_popia": "on",
        })
        self.assertEqual(parent_response.status_code, 200)
        parent_otp = OTPToken.objects.get(email="nomsa@example.com", role="parent")
        parent_response = self.client.post("/verify-otp", {
            "otp_session": str(parent_otp.id),
            "code": parent_otp.code,
        })
        self.assertRedirects(parent_response, "/welcome")
        self.assertEqual(self.client.get("/welcome").status_code, 200)
        self.assertEqual(self.client.get("/parent/dashboard").status_code, 200)

        self.client.get("/logout")
        teacher_response = self.client.post("/register", {
            "role": "teacher",
            "full_name": "Miss Khumalo",
            "email": "teacher@example.com",
            "school_name": "Thuthuka Primary",
            "grades_taught": "1,2",
            "password": "password123",
            "accepted_popia": "on",
        })
        self.assertEqual(teacher_response.status_code, 200)
        teacher_otp = OTPToken.objects.get(email="teacher@example.com", role="teacher")
        teacher_response = self.client.post("/verify-otp", {
            "otp_session": str(teacher_otp.id),
            "code": teacher_otp.code,
        })
        self.assertRedirects(teacher_response, "/teacher/dashboard")
        teacher = Teacher.objects.get(email="teacher@example.com")
        self.assertTrue(teacher.class_code)
        self.assertTrue(teacher.classes.exists())
        self.assertEqual(self.client.get("/teacher/dashboard").status_code, 200)

    def test_parent_can_add_child_with_teacher_class_code(self):
        parent = Parent.objects.create(
            full_name="Nomsa Dlamini",
            email="nomsa@example.com",
            password="hash",
            accepted_popia=True,
        )
        teacher = Teacher.objects.create(
            full_name="Miss Khumalo",
            email="teacher@example.com",
            school_name="Thuthuka Primary",
            grades_taught="1",
            password="hash",
            accepted_popia=True,
            class_code="TEACH1",
        )
        teacher_class = TeacherClass.objects.create(
            teacher=teacher,
            name="Grade 1 Readers",
            grade=1,
            class_code="CLASS1",
        )
        session = self.client.session
        session['account_role'] = 'parent'
        session['account_id'] = parent.id
        session['account_name'] = parent.full_name
        session.save()

        response = self.client.post("/parent/add-child", {
            "username": "lethum",
            "first_name": "Lethu",
            "last_name": "Mokoena",
            "age": 7,
            "grade": 1,
            "school_name": "",
            "class_code": teacher_class.class_code,
            "password": "password123",
        })
        self.assertRedirects(response, "/parent/dashboard")
        child = Child.objects.get(username__iexact="lethum")
        self.assertEqual(child.username, "Lethum")
        self.assertEqual(child.name, "Lethu Mokoena")
        self.assertEqual(child.parent_email, parent.email)
        self.assertEqual(child.teacher, teacher)
        self.assertEqual(child.teacher_class, teacher_class)
        self.assertEqual(child.school_name, teacher.school_name)

    def test_parent_add_child_page_has_username_and_photo_upload(self):
        parent = Parent.objects.create(
            full_name="Nomsa Dlamini",
            email="nomsa@example.com",
            password="hash",
            accepted_popia=True,
        )
        session = self.client.session
        session['account_role'] = 'parent'
        session['account_id'] = parent.id
        session['account_name'] = parent.full_name
        session.save()

        response = self.client.get("/parent/add-child")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="photo"')
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_parent_report_acknowledges_perfect_work(self):
        parent = Parent.objects.create(
            full_name="Nomsa Dlamini",
            email="nomsa@example.com",
            password="hash",
            accepted_popia=True,
        )
        child = Child.objects.create(
            parent=parent,
            username="star_reader",
            name="Star Reader",
            age=7,
            grade=1,
            parent_email=parent.email,
            password="hash",
        )
        Progress.objects.create(
            child=child,
            lesson=self.lesson,
            comprehension_score=4,
            visual_score=4,
            spelling_score=4,
            total_score=12,
            total_possible=12,
            stars_earned=3,
        )
        session = self.client.session
        session['account_role'] = 'parent'
        session['account_id'] = parent.id
        session['account_name'] = parent.full_name
        session.save()

        response = self.client.get(f"/dashboard/{child.id}/lessons/{self.lesson.id}")
        self.assertContains(response, "Good job! you got everything correct")

    def test_basic_routes_work_with_default_allowed_hosts(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/register").status_code, 200)

    def test_progress_pages_require_authorized_viewer(self):
        child = Child.objects.create(
            name="Sipho",
            age=7,
            grade=1,
            school_name="Thuthuka Primary",
            parent_email="sipho@example.com",
            password="hash",
        )
        other_child = Child.objects.create(
            name="Lerato",
            age=7,
            grade=1,
            school_name="Thuthuka Primary",
            parent_email="lerato@example.com",
            password="hash",
        )
        Progress.objects.create(child=child, lesson=self.lesson, total_score=1, total_possible=1, stars_earned=3)

        self.assertEqual(self.client.get(f"/dashboard/{child.id}").status_code, 302)
        self.assertEqual(
            self.client.get(f"/dashboard/{child.id}/lessons/{self.lesson.id}").status_code,
            302,
        )
        self.assertEqual(self.client.get(f"/api/progress/{child.id}").status_code, 403)

        self.sign_in_child(child)
        self.assertEqual(self.client.get(f"/dashboard/{child.id}").status_code, 200)
        self.assertEqual(
            self.client.get(f"/dashboard/{child.id}/lessons/{self.lesson.id}").status_code,
            200,
        )
        self.assertEqual(self.client.get(f"/api/progress/{child.id}").status_code, 200)
        self.assertEqual(self.client.get(f"/dashboard/{other_child.id}").status_code, 302)
        self.assertEqual(self.client.get(f"/api/progress/{other_child.id}").status_code, 403)

    def test_teacher_dashboard_does_not_fall_back_to_all_learners(self):
        Teacher.objects.create(
            full_name="Miss Khumalo",
            email="teacher@example.com",
            school_name="Empty Primary",
            grades_taught="1",
            password="hash",
            accepted_popia=True,
        )
        Child.objects.create(
            name="Learner At Another School",
            age=7,
            grade=1,
            school_name="Other Primary",
            parent_email="other@example.com",
            password="hash",
        )
        session = self.client.session
        teacher = Teacher.objects.get(email="teacher@example.com")
        session['account_role'] = 'teacher'
        session['account_id'] = teacher.id
        session['account_name'] = teacher.full_name
        session.save()

        response = self.client.get("/teacher/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Learner At Another School")
        self.assertContains(response, "No learners found yet.")

    def test_hidden_score_fields_do_not_control_saved_results(self):
        child = Child.objects.create(
            name="Sipho",
            age=7,
            grade=1,
            school_name="Thuthuka Primary",
            parent_email="sipho@example.com",
            password="hash",
        )
        spelling = self.lesson.spelling_activities.first()
        self.sign_in_child(child)

        response = self.client.post(f"/lessons/{self.lesson.id}/spelling", {
            f"activity_{spelling.id}": spelling.answer,
            "comprehension_score": "999",
            "comprehension_total": "999",
            "visual_score": "999",
            "visual_total": "999",
        })
        self.assertRedirects(response, f"/lessons/{self.lesson.id}/results")
        self.client.get(f"/lessons/{self.lesson.id}/results")

        progress = Progress.objects.get(child=child, lesson=self.lesson)
        self.assertEqual(progress.comprehension_score, 0)
        self.assertEqual(progress.visual_score, 0)
        self.assertEqual(progress.spelling_score, 1)
        self.assertEqual(progress.total_score, 1)

    def test_visual_answer_score_is_stored_server_side(self):
        child = Child.objects.create(
            name="Sipho",
            age=7,
            grade=1,
            school_name="Thuthuka Primary",
            parent_email="sipho@example.com",
            password="hash",
        )
        item = self.lesson.visual_items.first()
        self.sign_in_child(child)

        response = self.client.post("/api/check-visual-answer", json.dumps({
            "child_id": child.id,
            "lesson_id": self.lesson.id,
            "item_id": item.id,
            "selected_word": item.correct_word,
        }), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["visual_score"], 1)
        self.assertEqual(self.client.session[f"lesson_{self.lesson.id}_visual_score"], 1)

    def test_api_login_sets_session_for_scored_activity_calls(self):
        child = Child.objects.create(
            name="Sipho",
            age=7,
            grade=1,
            school_name="Thuthuka Primary",
            parent_email="sipho@example.com",
            password=make_password("password123"),
        )
        response = self.client.post("/api/login", json.dumps({
            "email": child.parent_email,
            "password": "password123",
        }), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["child_id"], child.id)

    def test_visual_activity_does_not_expose_correct_answer_before_answering(self):
        response = self.client.get(f"/api/lessons/{self.lesson.id}/visual-activity")

        self.assertEqual(response.status_code, 200)
        item_data = response.json()["items"][0]
        self.assertNotIn("correct_word", item_data)
        self.assertIn("word_options", item_data)

    def test_reading_activity_answer_is_hidden_until_submission(self):
        response = self.client.get(f"/api/lessons/{self.lesson.id}/questions")

        self.assertEqual(response.status_code, 200)
        activity_data = response.json()[0]
        self.assertEqual(activity_data["activity_type"], "multiple_choice")
        self.assertNotIn("correct_answer", activity_data)

    def test_reading_activity_is_checked_and_scored_server_side(self):
        child = Child.objects.create(
            name="Sipho",
            age=7,
            grade=1,
            parent_email="reading@example.com",
            password="hash",
        )
        self.sign_in_child(child)

        response = self.client.post("/api/check-reading-activity", json.dumps({
            "child_id": child.id,
            "lesson_id": self.lesson.id,
            "activity_id": self.reading_activity.id,
            "child_answer": "Market",
        }), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["correct"])
        self.assertEqual(response.json()["comprehension_score"], 1)
        self.assertEqual(self.client.session[f"lesson_{self.lesson.id}_comprehension_score"], 1)

        retry_response = self.client.post("/api/check-reading-activity", json.dumps({
            "child_id": child.id,
            "lesson_id": self.lesson.id,
            "activity_id": self.reading_activity.id,
            "child_answer": "School",
        }), content_type="application/json")

        self.assertEqual(retry_response.status_code, 200)
        self.assertFalse(retry_response.json()["correct"])
        self.assertEqual(retry_response.json()["comprehension_score"], 0)

    def test_structured_reading_activity_scores_each_item_and_skill(self):
        child = Child.objects.create(
            name="Sipho",
            age=10,
            grade=4,
            parent_email="structured@example.com",
            password="hash",
        )
        activity = ReadingActivity.objects.create(
            lesson=self.lesson,
            order=2,
            group_number=2,
            group_title='Crossword Puzzle',
            activity_type=ReadingActivity.CROSSWORD,
            skill='vocabulary_in_context',
            question='Complete the words.',
            options={'entries': []},
            correct_answer=json.dumps({'1-across': 'RUNNING', '2-down': 'NERVOUS'}),
        )
        self.sign_in_child(child)

        response = self.client.post("/api/check-reading-activity", json.dumps({
            "child_id": child.id,
            "lesson_id": self.lesson.id,
            "activity_id": activity.id,
            "child_answer": {'1-across': 'running', '2-down': 'happy'},
        }), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['partial'])
        self.assertEqual(response.json()['score_awarded'], 1)
        self.assertEqual(response.json()['score_possible'], 2)
        self.assertEqual(
            self.client.session[f"lesson_{self.lesson.id}_reading_skill_scores"]['vocabulary_in_context'],
            {'score': 1, 'total': 2},
        )

    def test_matching_list_answers_are_accepted_for_single_choice_questions(self):
        child = Child.objects.create(
            name='Mandu',
            age=10,
            grade=4,
            parent_email='grade4-matching-list@example.com',
            password='hash',
        )
        lesson = Lesson.objects.create(title='Grade 4 Matching Fix', grade=4)
        activity = ReadingActivity.objects.create(
            lesson=lesson,
            order=1,
            group_number=1,
            group_title='Story Words',
            activity_type=ReadingActivity.MATCHING,
            skill='vocabulary_in_context',
            question='What does unconscious mean in this report?',
            options=[
                'Not awake or responding',
                'Unable to hear a whisper',
                'Angry about an accident',
                'Ready to climb again',
            ],
            correct_answer='Not awake or responding',
        )
        self.sign_in_child(child)

        response = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': 'Not awake or responding',
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['correct'])
        self.assertEqual(response.json()['correct_answer'], 'Not awake or responding')

    def test_oral_activity_uses_dictation_textbox_for_activity_7(self):
        project_root = Path(__file__).resolve().parent.parent
        template = project_root / 'templates' / 'questions.html'
        source = template.read_text(encoding='utf-8')

        self.assertIn('function renderOral(activity)', source)
        self.assertIn("answer.id = 'oral-response'", source)
        self.assertIn('attachDictationToTextarea(answer)', source)
        self.assertIn('SpeechRecognition', source)

    def test_sequence_activity_supports_drag_and_drop_reordering(self):
        project_root = Path(__file__).resolve().parent.parent
        template = project_root / 'templates' / 'questions.html'
        source = template.read_text(encoding='utf-8')

        self.assertIn("row.draggable = true", source)
        self.assertIn("row.addEventListener('dragover'", source)
        self.assertIn("row.addEventListener('drop'", source)
        self.assertIn('sequence-draggable', source)

    def test_grade_four_matching_returns_row_level_correct_answers(self):
        child = Child.objects.create(
            name='Mandu',
            age=10,
            grade=4,
            parent_email='grade4-matching@example.com',
            password='hash',
        )
        lesson = Lesson.objects.create(title='Grade 4 Word Detective', grade=4)
        activity = ReadingActivity.objects.create(
            lesson=lesson,
            order=1,
            group_number=1,
            group_title='Word Detective',
            activity_type=ReadingActivity.MATCHING,
            skill='vocabulary_in_context',
            question='Match each word with its meaning.',
            options={
                'prompts': [
                    {'key': '1', 'text': 'practised'},
                    {'key': '2', 'text': 'grateful'},
                ],
                'choices': [
                    {'key': 'a', 'text': 'did something repeatedly'},
                    {'key': 'b', 'text': 'feeling thankful'},
                ],
            },
            correct_answer=json.dumps({'1': 'a', '2': 'b'}),
        )
        self.sign_in_child(child)

        response = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': {'1': 'a', '2': 'a'},
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['score_awarded'], 1)
        self.assertEqual(response.json()['score_possible'], 2)
        self.assertEqual(response.json()['correct_answer'], {'1': 'a', '2': 'b'})

    def test_word_scramble_returns_row_answers_for_colour_coded_feedback(self):
        child = Child.objects.create(
            name='Mandu',
            age=10,
            grade=4,
            parent_email='grade4-scramble@example.com',
            password='hash',
        )
        lesson = Lesson.objects.create(title='Grade 4 Spelling', grade=4)
        activity = ReadingActivity.objects.create(
            lesson=lesson,
            order=1,
            group_number=1,
            group_title='Spelling Activity',
            activity_type=ReadingActivity.WORD_SCRAMBLE,
            skill='spelling',
            question='Unscramble the words.',
            options={'items': [
                {'key': '1', 'scramble': 'OSHSE'},
                {'key': '2', 'scramble': 'NIRNGNU'},
            ]},
            correct_answer=json.dumps({'1': 'SHOES', '2': 'RUNNING'}),
        )
        self.sign_in_child(child)

        response = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': {'1': 'shoes', '2': 'wrong'},
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['score_awarded'], 1)
        self.assertEqual(response.json()['score_possible'], 2)
        self.assertEqual(response.json()['correct_answer'], {'1': 'SHOES', '2': 'RUNNING'})
        questions_page = self.client.get(f'/lessons/{lesson.id}/questions')
        self.assertContains(questions_page, 'function markScrambleAnswers')
        stylesheet = Path(__file__).resolve().parent.parent / 'static' / 'css' / 'sgila_app.css'
        self.assertIn('.scramble-row.scramble-correct', stylesheet.read_text(encoding='utf-8'))
        self.assertIn('.scramble-row.scramble-wrong', stylesheet.read_text(encoding='utf-8'))

    def test_reasoning_requires_readable_english_and_matches_example_sentence(self):
        child = Child.objects.create(
            name='Mandu',
            age=10,
            grade=4,
            parent_email='reasoning@example.com',
            password='hash',
        )
        lesson = Lesson.objects.create(title='Reasoning Check', grade=4)
        activity = ReadingActivity.objects.create(
            lesson=lesson,
            order=1,
            group_number=1,
            group_title='Story thinking',
            activity_type=ReadingActivity.REASONING,
            skill='inference',
            question='Why were the first-aid kits important?',
            correct_answer='because it was used to help the dog get better',
        )
        self.sign_in_child(child)

        bad_response = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': "rsfkhdfjlgb'oil",
        }), content_type='application/json')
        self.assertEqual(bad_response.status_code, 400)
        self.assertIn('not clear enough', bad_response.json()['error'])

        good_response = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': 'because it was used to help the dog get better',
        }), content_type='application/json')
        self.assertEqual(good_response.status_code, 200)
        self.assertTrue(good_response.json()['review_required'])
        self.assertEqual(good_response.json()['model_answer'], 'because it was used to help the dog get better')

    def test_text_answers_reject_gibberish_and_allow_capitalised_name(self):
        child = Child.objects.create(
            name='Amina',
            age=10,
            grade=4,
            parent_email='sensible-answers@example.com',
            password='hash',
        )
        lesson = Lesson.objects.create(title='Sensible answer check', grade=4)
        activity = ReadingActivity.objects.create(
            lesson=lesson,
            order=1,
            group_number=1,
            group_title='Prediction',
            activity_type=ReadingActivity.PREDICTION,
            skill='prediction',
            question='Who do you think will come next?',
            correct_answer='Amina',
        )
        self.sign_in_child(child)

        gibberish = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': 'xqzv lqkzro mntp',
        }), content_type='application/json')
        self.assertEqual(gibberish.status_code, 400)
        self.assertIn('not clear enough', gibberish.json()['error'])

        vowel_gibberish = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': 'Aeiou qwerty',
        }), content_type='application/json')
        self.assertEqual(vowel_gibberish.status_code, 400)
        self.assertIn('not clear enough', vowel_gibberish.json()['error'])

        valid_name = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': 'Mandla',
        }), content_type='application/json')
        self.assertEqual(valid_name.status_code, 200)

    def test_open_ended_response_requires_two_punctuated_sentences(self):
        child = Child.objects.create(
            name='Twins learner',
            age=10,
            grade=4,
            parent_email='two-sentences@example.com',
            password='hash',
        )
        lesson = Lesson.objects.create(title='Two Sentence Check', grade=4)
        activity = ReadingActivity.objects.create(
            lesson=lesson,
            order=1,
            group_number=1,
            group_title='Retell',
            activity_type=ReadingActivity.OPEN_ENDED,
            skill='summarising',
            question='Retell the mistake and resolution in two or three sentences.',
            correct_answer='Todd and Ted dressed for Comic Day on the wrong date. They felt embarrassed at school but then laughed at the harmless mistake.',
        )
        self.sign_in_child(child)

        short_response = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': 'The twins made a mistake',
        }), content_type='application/json')
        self.assertEqual(short_response.status_code, 400)
        self.assertIn('two or more sentences', short_response.json()['error'])

        complete_response = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': 'The twins made a mistake. They laughed about it later.',
        }), content_type='application/json')
        self.assertEqual(complete_response.status_code, 200)

    def test_guided_diary_is_saved_to_the_child_story_profile(self):
        child = Child.objects.create(
            name="Mandu",
            age=9,
            grade=3,
            parent_email="diary@example.com",
            password="hash",
        )
        activity = ReadingActivity.objects.create(
            lesson=self.lesson,
            order=2,
            group_number=7,
            group_title='My Diary',
            activity_type=ReadingActivity.REASONING,
            skill='text_to_self',
            question='Write your own diary entry.',
            options={
                'writing_template': True,
                'feelings': ['happy', 'proud'],
            },
            correct_answer='Any complete diary entry.',
        )
        self.sign_in_child(child)
        answer = {
            'feeling': 'proud',
            'because': 'I helped my friend keep a secret',
            'best_part': 'we solved the problem together',
            'next_time': 'write down my thoughts',
            'from_name': 'Mandu',
        }

        response = self.client.post('/api/check-reading-activity', json.dumps({
            'child_id': child.id,
            'lesson_id': self.lesson.id,
            'activity_id': activity.id,
            'child_answer': answer,
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])
        self.assertEqual(response.json()['message'], 'Your diary entry is saved to your profile, Mandu.')
        saved = ReadingActivityResponse.objects.get(child=child, lesson=self.lesson)
        self.assertEqual(saved.response, answer)

    def test_dashboard_lists_grade_stories_and_opens_dynamic_story_report(self):
        parent = Parent.objects.create(
            full_name="Nomsa Dlamini",
            email="dynamic@example.com",
            password="hash",
            accepted_popia=True,
        )
        child = Child.objects.create(
            parent=parent,
            name="Mandu",
            age=10,
            grade=4,
            parent_email=parent.email,
            photo="child_photos/mandu.jpg",
            password="hash",
        )
        completed_lesson = Lesson.objects.create(title="Mandu's Running Shoes", grade=4)
        incomplete_lesson = Lesson.objects.create(title="Why Mapula Missed School", grade=4)
        Progress.objects.create(
            child=child,
            lesson=completed_lesson,
            total_score=6,
            total_possible=10,
            stars_earned=1,
            assessment_scores={
                'inference': {'score': 1, 'total': 3},
                'spelling': {'score': 5, 'total': 7},
            },
        )
        ReadingActivityResponse.objects.create(
            child=child,
            lesson=completed_lesson,
            response={
                'feeling': 'proud',
                'because': 'I kept trying',
                'best_part': 'finishing the race',
                'next_time': 'run with a friend',
                'from_name': 'Mandu',
            },
        )
        session = self.client.session
        session['account_role'] = 'parent'
        session['account_id'] = parent.id
        session.save()

        response = self.client.get(f"/dashboard/{child.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Running Shoes")
        self.assertContains(response, "Why Mapula Missed School")
        self.assertContains(response, '1 of 2 stories completed')
        self.assertContains(response, 'View detailed report')
        self.assertContains(response, 'id="story-search"')
        self.assertContains(response, 'id="story-sort"')
        self.assertContains(response, 'Recently completed')
        self.assertContains(response, 'Stars: high to low')
        self.assertNotContains(response, 'Activity scores')
        self.assertEqual(len(response.context['story_rows']), 2)

        searched = self.client.get(f"/dashboard/{child.id}", {'q': 'Mapula'})
        self.assertContains(searched, 'Why Mapula Missed School')
        self.assertNotContains(searched, 'Running Shoes')
        self.assertEqual(searched.context['visible_story_count'], 1)

        sorted_response = self.client.get(
            f"/dashboard/{child.id}",
            {'sort': 'title_desc'},
        )
        self.assertEqual(
            [item['lesson'].title for item in sorted_response.context['story_rows']],
            ['Why Mapula Missed School', "Mandu's Running Shoes"],
        )

        detail = self.client.get(
            f"/dashboard/{child.id}/lessons/{completed_lesson.id}"
        )
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, 'Skills tested in this story')
        self.assertContains(detail, 'class="story-detail-avatar has-photo"')
        self.assertContains(detail, 'src="/media/child_photos/mandu.jpg"')
        self.assertContains(detail, 'Inference')
        self.assertContains(detail, 'Spelling')
        self.assertContains(detail, 'Focus areas for this story')
        self.assertContains(detail, "Mandu's story connection")
        self.assertContains(detail, 'finishing the race')
        self.assertEqual(
            {row['key'] for row in detail.context['breakdown']},
            {'inference', 'spelling'},
        )

        locked = self.client.get(
            f"/dashboard/{child.id}/lessons/{incomplete_lesson.id}"
        )
        self.assertRedirects(locked, f"/dashboard/{child.id}")

    def test_grade_three_reports_hide_retired_sequence_and_visual_scores(self):
        parent = Parent.objects.create(
            full_name='Grade Three Parent',
            email='grade3-report@example.com',
            password='hash',
            accepted_popia=True,
        )
        child = Child.objects.create(
            parent=parent,
            name='Thato',
            age=9,
            grade=3,
            parent_email=parent.email,
            password='hash',
        )
        lesson = Lesson.objects.create(title='Retired Activity Report', grade=3)
        Progress.objects.create(
            child=child,
            lesson=lesson,
            total_score=6,
            total_possible=8,
            stars_earned=2,
            assessment_scores={
                'literal_comprehension': {'score': 1, 'total': 2},
                'sequencing': {'score': 1, 'total': 1},
                'visual_literacy': {'score': 4, 'total': 5},
            },
        )
        session = self.client.session
        session['account_role'] = 'parent'
        session['account_id'] = parent.id
        session.save()

        dashboard = self.client.get(f'/dashboard/{child.id}')
        detail = self.client.get(f'/dashboard/{child.id}/lessons/{lesson.id}')

        self.assertEqual(dashboard.context['story_rows'][0]['assessment_count'], 1)
        self.assertEqual(dashboard.context['story_rows'][0]['percentage'], 50)
        self.assertEqual(detail.context['report_percentage'], 50)
        self.assertEqual(
            {row['key'] for row in detail.context['breakdown']},
            {'literal_comprehension'},
        )
        self.assertNotContains(detail, 'Visual matching')
        self.assertNotContains(detail, 'Sequencing')

    def test_questions_page_uses_a_guided_child_friendly_flow(self):
        child = Child.objects.create(
            name="Sipho",
            age=7,
            grade=1,
            parent_email="guided@example.com",
            password="hash",
        )
        self.sign_in_child(child)

        response = self.client.get(f"/lessons/{self.lesson.id}/questions")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lesson.title)
        self.assertContains(response, 'id="activity-map"')
        self.assertContains(response, 'const childName = "Sipho";')
        self.assertContains(response, 'markMatchingAnswers(data);')
        self.assertContains(response, "badge.textContent = isCorrect ? 'Correct' : 'Incorrect';")
        self.assertContains(response, 'Correct match:')
        self.assertContains(response, "Choose the best answer, then check it.")
        self.assertContains(response, "Say your answer out loud. You do not need to type.")
        self.assertContains(response, "I said my answer")
        self.assertNotContains(response, "Type the words you said.")

    def test_spelling_page_and_api_do_not_expose_answers_before_answering(self):
        child = Child.objects.create(
            name="Sipho",
            age=7,
            grade=1,
            school_name="Thuthuka Primary",
            parent_email="spelling@example.com",
            password="hash",
        )
        self.sign_in_child(child)

        page_response = self.client.get(f"/lessons/{self.lesson.id}/spelling")
        api_response = self.client.get(f"/api/lessons/{self.lesson.id}/spelling")

        self.assertEqual(page_response.status_code, 200)
        self.assertNotContains(page_response, "data-answer")
        self.assertEqual(api_response.status_code, 200)
        self.assertNotContains(api_response, "\"answer\"")

    def test_spelling_answer_feedback_is_checked_server_side(self):
        child = Child.objects.create(
            name="Sipho",
            age=7,
            grade=1,
            school_name="Thuthuka Primary",
            parent_email="feedback@example.com",
            password="hash",
        )
        spelling = self.lesson.spelling_activities.first()
        self.sign_in_child(child)

        response = self.client.post("/api/check-spelling-answer", json.dumps({
            "child_id": child.id,
            "lesson_id": self.lesson.id,
            "activity_id": spelling.id,
            "answer": spelling.answer,
        }), content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["correct"])

    def test_empty_story_and_visual_sections_do_not_trap_learner(self):
        child = Child.objects.create(
            name="Sipho",
            age=7,
            grade=1,
            school_name="Thuthuka Primary",
            parent_email="empty@example.com",
            password="hash",
        )
        empty_lesson = Lesson.objects.create(title="Empty Draft", grade=1)
        self.sign_in_child(child)

        story_response = self.client.get(f"/lessons/{empty_lesson.id}/story")
        visual_response = self.client.get(f"/lessons/{empty_lesson.id}/visual-activity")

        self.assertEqual(story_response.status_code, 200)
        self.assertContains(story_response, "No story pages have been added yet.")
        self.assertContains(story_response, "Start 3 activities")
        self.assertEqual(visual_response.status_code, 200)
        self.assertContains(visual_response, "No visual matching cards have been added yet.")
        self.assertContains(visual_response, "Continue")

    def test_grade_three_visual_matching_choice_opens_its_own_activity(self):
        child = Child.objects.create(
            name="Mandu",
            age=9,
            grade=3,
            parent_email="grade3-flow@example.com",
            password="hash",
        )
        lesson = Lesson.objects.create(title="Grade 3 Flow", grade=3)
        ReadingActivity.objects.create(
            lesson=lesson,
            order=1,
            activity_type=ReadingActivity.MULTIPLE_CHOICE,
            skill='literal_comprehension',
            question='What did Mandu find?',
            options=['A clue', 'A map'],
            correct_answer='A clue',
        )
        PronunciationWord.objects.create(lesson=lesson, word='Clue')
        SpellingActivity.objects.create(
            lesson=lesson,
            activity_type=SpellingActivity.FILL_VOWEL,
            display_text='cl_e',
            answer='clue',
        )
        self.sign_in_child(child)

        questions_response = self.client.get(f'/lessons/{lesson.id}/questions')
        visual_response = self.client.get(f'/lessons/{lesson.id}/visual-activity')

        self.assertEqual(questions_response.context['next_activity_url'], f'/lessons/{lesson.id}/pronunciation')
        self.assertEqual(visual_response.status_code, 200)
        self.assertContains(visual_response, "No visual matching cards have been added yet.")

    def create_parent_and_child(self, subscription_status=None, link_by_email_only=False):
        parent = Parent.objects.create(
            full_name='Nandi Dlamini',
            email='nandi@example.com',
            password=make_password('StrongPass123!'),
            accepted_popia=True,
        )
        child = Child.objects.create(
            parent=None if link_by_email_only else parent,
            username='lwazi',
            name='Lwazi Dlamini',
            age=8,
            grade=1,
            parent_email=parent.email,
            password=make_password('LearnerPass123!'),
        )
        if subscription_status:
            Subscription.objects.create(
                parent=parent,
                plan_type='family',
                status=subscription_status,
            )
        return parent, child

    def sign_in_parent(self, parent):
        session = self.client.session
        session['account_role'] = 'parent'
        session['account_id'] = parent.id
        session['account_name'] = parent.full_name
        session.save()

    def test_parent_deactivation_requires_password_and_blocks_existing_learner_sessions(self):
        parent, child = self.create_parent_and_child()
        self.sign_in_parent(parent)

        wrong_password = self.client.post('/parent/deactivate', {'password': 'wrong'})
        self.assertRedirects(wrong_password, '/parent/dashboard')
        parent.refresh_from_db()
        self.assertTrue(parent.is_active)

        learner_client = Client()
        learner_session = learner_client.session
        learner_session.update({
            'account_role': 'learner',
            'account_id': child.id,
            'account_name': child.name,
            'child_id': child.id,
            'child_name': child.name,
            'child_grade': child.grade,
        })
        learner_session.save()

        response = self.client.post('/parent/deactivate', {'password': 'StrongPass123!'})
        self.assertRedirects(response, '/login?role=parent')
        parent.refresh_from_db()
        self.assertFalse(parent.is_active)
        self.assertIsNotNone(parent.deactivated_at)
        self.assertEqual(parent.auth_version, 1)
        self.assertTrue(Child.objects.filter(pk=child.pk).exists())
        self.assertNotIn('account_role', self.client.session)

        blocked = learner_client.get(f'/grade/{child.grade}')
        self.assertRedirects(blocked, '/account-access?reason=parent_deactivated')
        self.assertNotIn('child_id', learner_client.session)

    def test_email_only_legacy_child_is_blocked_when_parent_is_deactivated(self):
        parent, child = self.create_parent_and_child(link_by_email_only=True)
        parent.is_active = False
        parent.save(update_fields=['is_active'])

        response = self.client.post('/api/login', {
            'email': child.username,
            'password': 'LearnerPass123!',
            'role': 'learner',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['reason'], 'parent_deactivated')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_parent_reactivation_uses_a_hashed_one_time_code(self):
        parent, child = self.create_parent_and_child()
        parent.is_active = False
        parent.auth_version = 1
        parent.save(update_fields=['is_active', 'auth_version'])

        login_response = self.client.post('/login', {
            'role': 'parent',
            'email': parent.email,
            'password': 'StrongPass123!',
        })
        self.assertRedirects(login_response, '/account/reactivate')
        self.assertNotIn('account_role', self.client.session)

        send_response = self.client.post('/account/reactivate', {'action': 'send'})
        self.assertRedirects(send_response, '/account/reactivate?sent=1')
        self.assertEqual(len(mail.outbox), 1)
        code = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)
        token = AccountActionOTP.objects.get(parent=parent)
        self.assertNotEqual(token.code_hash, code)

        verify_response = self.client.post('/account/reactivate', {
            'action': 'verify',
            'code': code,
        })
        self.assertRedirects(verify_response, '/parent/dashboard')
        parent.refresh_from_db()
        token.refresh_from_db()
        self.assertTrue(parent.is_active)
        self.assertIsNone(parent.deactivated_at)
        self.assertEqual(parent.auth_version, 2)
        self.assertTrue(token.is_used)
        self.assertEqual(Parent.objects.filter(email=parent.email).count(), 1)

        learner_login = Client().post('/login', {
            'role': 'learner',
            'email': child.username,
            'password': 'LearnerPass123!',
        })
        self.assertRedirects(learner_login, f'/grade/{child.grade}')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_wrong_reactivation_code_is_limited_to_five_attempts(self):
        parent, _ = self.create_parent_and_child()
        parent.is_active = False
        parent.save(update_fields=['is_active'])
        self.client.post('/login', {
            'role': 'parent',
            'email': parent.email,
            'password': 'StrongPass123!',
        })
        self.client.post('/account/reactivate', {'action': 'send'})

        for _ in range(AccountActionOTP.MAX_ATTEMPTS):
            self.client.post('/account/reactivate', {'action': 'verify', 'code': '000000'})

        token = AccountActionOTP.objects.get(parent=parent)
        parent.refresh_from_db()
        self.assertEqual(token.attempts, AccountActionOTP.MAX_ATTEMPTS)
        self.assertTrue(token.is_used)
        self.assertFalse(parent.is_active)

        resend_response = self.client.post('/account/reactivate', {'action': 'send'})
        self.assertRedirects(resend_response, '/account/reactivate')
        self.assertEqual(AccountActionOTP.objects.filter(parent=parent).count(), 1)
        self.assertNotIn('reactivation_token_id', self.client.session)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_cancelled_plan_keeps_learners_paused_after_parent_reactivation(self):
        parent, child = self.create_parent_and_child(subscription_status='cancelled')
        parent.is_active = False
        parent.save(update_fields=['is_active'])
        self.client.post('/login', {
            'role': 'parent',
            'email': parent.email,
            'password': 'StrongPass123!',
        })
        self.client.post('/account/reactivate', {'action': 'send'})
        code = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)

        response = self.client.post('/account/reactivate', {'action': 'verify', 'code': code})
        self.assertRedirects(response, '/subscription')
        parent.refresh_from_db()
        self.assertTrue(parent.is_active)

        learner_response = Client().post('/login', {
            'role': 'learner',
            'email': child.username,
            'password': 'LearnerPass123!',
        })
        self.assertRedirects(learner_response, '/account-access?reason=subscription_inactive')

    def test_deactivation_can_cancel_subscription_without_deleting_records(self):
        parent, child = self.create_parent_and_child(subscription_status='active')
        self.sign_in_parent(parent)
        response = self.client.post('/parent/deactivate', {
            'password': 'StrongPass123!',
            'cancel_subscription': 'on',
        })

        self.assertRedirects(response, '/login?role=parent')
        self.assertEqual(Subscription.objects.get(parent=parent).status, 'cancelled')
        self.assertTrue(Child.objects.filter(pk=child.pk).exists())

    def test_failed_reactivation_email_does_not_leave_a_usable_token(self):
        parent, _ = self.create_parent_and_child()
        parent.is_active = False
        parent.save(update_fields=['is_active'])
        self.client.post('/login', {
            'role': 'parent',
            'email': parent.email,
            'password': 'StrongPass123!',
        })

        with patch('lessons.views.send_mail', side_effect=RuntimeError('smtp unavailable')):
            response = self.client.post('/account/reactivate', {'action': 'send'})

        self.assertRedirects(response, '/account/reactivate')
        self.assertFalse(AccountActionOTP.objects.filter(parent=parent).exists())
        parent.refresh_from_db()
        self.assertFalse(parent.is_active)

    def test_story_page_lists_available_activities_for_learner_choice(self):
        child = Child.objects.create(
            name='Activity chooser',
            age=9,
            grade=3,
            parent_email='activity-chooser@example.com',
            password='hash',
        )
        lesson = Lesson.objects.create(title='Choose Activities', grade=3)
        ReadingActivity.objects.create(
            lesson=lesson,
            order=1,
            activity_type=ReadingActivity.MULTIPLE_CHOICE,
            skill='literal_comprehension',
            question='What happened?',
            options=['A', 'B'],
            correct_answer='A',
        )
        PronunciationWord.objects.create(lesson=lesson, word='Story')
        SpellingActivity.objects.create(
            lesson=lesson,
            activity_type=SpellingActivity.FILL_VOWEL,
            display_text='st_ry',
            answer='story',
        )
        self.sign_in_child(child)

        response = self.client.get(f'/lessons/{lesson.id}/story')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/lessons/{lesson.id}/questions')
        self.assertContains(response, f'/lessons/{lesson.id}/pronunciation')
        self.assertContains(response, f'/lessons/{lesson.id}/spelling')


class CurriculumSeedTests(TestCase):
    def test_seeded_curriculum_content_is_limited_to_grades_one_to_four(self):
        call_command('seed_data', verbosity=0)

        self.assertEqual(set(Lesson.objects.values_list('grade', flat=True)), {1, 2, 3, 4})
        self.assertFalse(Lesson.objects.filter(pages__text__icontains='practice story').exists())
        for grade in range(1, 5):
            self.assertEqual(Lesson.objects.filter(grade=grade).count(), 5)
            for lesson in Lesson.objects.filter(grade=grade):
                self.assertGreaterEqual(lesson.pages.count(), 3)
                expected_minimum = 5 if grade == 3 else grade + 3
                self.assertGreaterEqual(lesson.reading_activities.count(), expected_minimum)
                expected_visual_count = 0 if grade == 3 else 5
                self.assertEqual(lesson.visual_items.count(), expected_visual_count)
                expected_pronunciation_count = 8 if lesson.title in PRONUNCIATION_WORDS else 5
                self.assertEqual(lesson.pronunciation_words.count(), expected_pronunciation_count)
                if grade == 3:
                    self.assertEqual(lesson.sequencing_activities.count(), 0)
                    self.assertFalse(
                        lesson.reading_activities.filter(
                            activity_type__in={
                                ReadingActivity.SEQUENCING,
                                ReadingActivity.TRUE_FALSE,
                            },
                        ).exists()
                    )
                for visual_item in lesson.visual_items.all():
                    self.assertEqual(len(visual_item.get_word_options()), 5)
                    self.assertIn(visual_item.correct_word, visual_item.get_word_options())

    def test_soccer_trouble_choice_activity_is_answerable(self):
        call_command('seed_data', verbosity=0)
        child = Child.objects.create(
            name='Soccer learner',
            age=9,
            grade=3,
            parent_email='soccer@example.com',
            password='hash',
        )
        lesson = Lesson.objects.get(title='Soccer Trouble')
        activity = lesson.reading_activities.get(question='What did Coach Jones tell John to do?')
        session = self.client.session
        session.update({
            'account_role': 'learner',
            'account_id': child.id,
            'account_name': child.name,
            'child_id': child.id,
            'child_name': child.name,
            'child_grade': child.grade,
        })
        session.save()

        response = self.client.post('/api/check-reading-activity', data={
            'child_id': child.id,
            'lesson_id': lesson.id,
            'activity_id': activity.id,
            'child_answer': 'Look at the goal and kick.',
        }, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['correct'])
        self.assertEqual(activity.activity_type, ReadingActivity.MULTIPLE_CHOICE)

        formats = set(ReadingActivity.objects.values_list('activity_type', flat=True))
        self.assertTrue({
            ReadingActivity.MULTIPLE_CHOICE,
            ReadingActivity.TRUE_FALSE,
            ReadingActivity.SEQUENCING,
            ReadingActivity.ORAL_RESPONSE,
            ReadingActivity.OPEN_ENDED,
            ReadingActivity.PREDICTION,
            ReadingActivity.REASONING,
            ReadingActivity.CLOZE,
            ReadingActivity.MATCHING,
            ReadingActivity.CROSSWORD,
            ReadingActivity.WORD_SCRAMBLE,
        }.issubset(formats))

        hot_day = Lesson.objects.get(title='A Very Hot Day')
        self.assertEqual(
            list(hot_day.reading_activities.values_list('activity_type', flat=True)[:3]),
            [ReadingActivity.CLOZE] * 3,
        )
        running_story = Lesson.objects.get(title="Mandu's Running Shoes")
        self.assertEqual(running_story.reading_activities.count(), 13)
        self.assertEqual(
            list(running_story.reading_activities.values_list('group_number', flat=True)),
            ([1] * 10) + [2, 3, 4],
        )
        self.assertEqual(running_story.reading_activities.first().activity_type, ReadingActivity.MULTIPLE_CHOICE)
        running_choices = list(running_story.reading_activities.filter(group_number=1))
        running_answer_positions = [
            activity.options.index(activity.correct_answer)
            for activity in running_choices
        ]
        self.assertEqual(running_answer_positions, [2, 0, 3, 1, 2, 1, 3, 0, 2, 1])
        self.assertEqual(set(running_answer_positions), {0, 1, 2, 3})
        self.assertEqual(
            list(running_story.reading_activities.filter(group_number__gt=1).values_list('activity_type', flat=True)),
            [ReadingActivity.CROSSWORD, ReadingActivity.MATCHING, ReadingActivity.WORD_SCRAMBLE],
        )
        self.assertEqual(
            running_story.reading_activities.get(activity_type=ReadingActivity.MATCHING).group_title,
            'Word Detective',
        )
        diary_story = Lesson.objects.get(title="Mandu's Secret Diary")
        self.assertEqual(diary_story.reading_activities.count(), 5)
        self.assertEqual(
            list(diary_story.reading_activities.values_list('group_number', flat=True)),
            [1, 1, 1, 2, 3],
        )
        self.assertEqual(
            list(diary_story.pronunciation_words.values_list('word', flat=True)),
            ['Diary', 'Secret', 'Hide', 'Clue', 'Blond', 'Flour', 'Footprint', 'Culprit'],
        )
        diary_pronunciation_images = [
            f'/static/img/pronunciation/mandu_secret_diary/{word}.png'
            for word in ['diary', 'secret', 'hide', 'clue', 'blond', 'flour', 'footprint', 'culprit']
        ]
        self.assertEqual(
            list(diary_story.pronunciation_words.values_list('image_url', flat=True)),
            diary_pronunciation_images,
        )
        static_root = Path(__file__).resolve().parent.parent / 'static'
        self.assertTrue(all(
            (static_root / image_url.removeprefix('/static/')).is_file()
            for image_url in diary_pronunciation_images
        ))
        self.assertEqual(
            list(diary_story.spelling_activities.values_list('display_text', 'answer')),
            LESSON_SPELLING["Mandu's Secret Diary"],
        )
        diary_story_text = ' '.join(diary_story.pages.values_list('text', flat=True))
        self.assertIn('relieved and amused', diary_story_text)
        self.assertIn('much better hiding place', diary_story_text)
        self.assertEqual(set(Lesson.objects.values_list('title', flat=True)), set(LESSON_WORDS))

        activity_signatures = {
            tuple(lesson.reading_activities.values_list('activity_type', flat=True))
            for lesson in Lesson.objects.all()
        }
        self.assertGreaterEqual(len(activity_signatures), 15)

        bongi_story = Lesson.objects.get(title='Bongi Waits')
        self.assertIn(
            'baby brother, Siya',
            ' '.join(bongi_story.pages.values_list('text', flat=True)),
        )

        for title, filename in VISUAL_VOCAB_SHEETS.items():
            lesson = Lesson.objects.get(title=title)
            expected_images = [
                f'/static/img/vocab_sheets/{filename}#panel-{panel}'
                for panel in range(1, 6)
            ]
            expected_visual_images = [] if lesson.grade == 3 else expected_images
            self.assertEqual(
                list(lesson.visual_items.values_list('image_url', flat=True)),
                expected_visual_images,
            )
            if title not in PRONUNCIATION_WORDS:
                self.assertEqual(
                    list(lesson.pronunciation_words.values_list('image_url', flat=True)),
                    expected_images,
                )

        for title in STORYBOARD_IMAGES:
            lesson = Lesson.objects.get(title=title)
            storyboard_path = f'/static/img/storyboards/{STORYBOARD_IMAGES[title][0]}'
            if title in LESSON_COVERS:
                self.assertEqual(lesson.thumbnail_image, LESSON_COVERS[title])
            else:
                self.assertEqual(lesson.thumbnail_image, storyboard_path)
            page_images = list(lesson.pages.values_list('image_url', flat=True))
            self.assertEqual(
                [int(image_url.rsplit('#panel-', 1)[1]) for image_url in page_images],
                STORYBOARD_PAGE_PANELS[title],
            )
            self.assertTrue(all(
                image_url.split('#', 1)[0] == storyboard_path
                for image_url in page_images
            ))


class GradeConfirmationTests(TestCase):
    """Covers the yearly grade-confirmation feature: no auto-rollover, an
    explicit human decision is required, and it's fully logged."""

    def setUp(self):
        self.client = Client()
        self.parent = Parent.objects.create(
            full_name='Test Parent', email='parent-gc@example.com',
            password=make_password('password123'), accepted_popia=True,
        )
        self.teacher = Teacher.objects.create(
            full_name='Test Teacher', email='teacher-gc@example.com',
            password=make_password('password123'), school_name='Sgila Primary',
            grades_taught='2,3', accepted_popia=True,
        )
        self.child = Child.objects.create(
            name='Test Learner', username='testlearnergc', grade=2,
            parent=self.parent, parent_email=self.parent.email,
            school_name='Sgila Primary', teacher=self.teacher,
            password=make_password('password123'),
        )

    def login_parent(self):
        return self.client.post('/login', {'role': 'parent', 'email': self.parent.email, 'password': 'password123'})

    def login_teacher(self):
        return self.client.post('/login', {'role': 'teacher', 'email': self.teacher.email, 'password': 'password123'})

    def test_registration_confirms_current_year_and_needs_no_prompt(self):
        self.assertEqual(self.child.grade_confirmed_year, None)
        # Simulate what register_learner/parent_add_child do on creation.
        from lessons.views import mark_grade_confirmed_at_registration
        mark_grade_confirmed_at_registration(self.child)
        self.child.refresh_from_db()
        self.assertEqual(self.child.grade_confirmed_year, current_school_year())
        self.assertFalse(self.child.needs_grade_confirmation())
        self.assertEqual(
            GradeHistory.objects.get(child=self.child).confirmed_by,
            GradeHistory.REGISTRATION,
        )

    def test_grade_never_changes_on_its_own(self):
        """Simulates a new school year starting with nobody confirming anything:
        the app must not touch `grade` by itself."""
        self.child.grade_confirmed_year = current_school_year() - 1
        self.child.save(update_fields=['grade_confirmed_year'])
        self.assertTrue(self.child.needs_grade_confirmation())

        self.login_parent()
        response = self.client.get('/parent/dashboard')
        self.assertContains(response, 'confirm')
        self.assertContains(response, 'Test Learner')

        self.child.refresh_from_db()
        self.assertEqual(self.child.grade, 2)  # untouched

    def test_parent_can_confirm_promotion(self):
        self.child.grade_confirmed_year = current_school_year() - 1
        self.child.save(update_fields=['grade_confirmed_year'])
        self.login_parent()

        response = self.client.post(f'/confirm-grade/{self.child.id}', {'grade': '3'}, follow=True)
        self.assertEqual(response.status_code, 200)

        self.child.refresh_from_db()
        self.assertEqual(self.child.grade, 3)
        self.assertEqual(self.child.grade_confirmed_year, current_school_year())
        self.assertFalse(self.child.needs_grade_confirmation())

        history = GradeHistory.objects.get(child=self.child, year=current_school_year())
        self.assertEqual(history.grade, 3)
        self.assertEqual(history.confirmed_by, GradeHistory.PARENT)
        self.assertFalse(history.repeated)

    def test_parent_can_confirm_a_repeated_grade(self):
        self.child.grade_confirmed_year = current_school_year() - 1
        self.child.save(update_fields=['grade_confirmed_year'])
        self.login_parent()

        self.client.post(f'/confirm-grade/{self.child.id}', {'grade': '2'})

        self.child.refresh_from_db()
        self.assertEqual(self.child.grade, 2)  # repeated, not bumped

        history = GradeHistory.objects.get(child=self.child, year=current_school_year())
        self.assertEqual(history.grade, 2)
        # Registration already logged grade 2 for the child's first year, so a
        # later parent confirmation of the same grade is correctly flagged as a repeat.
        self.assertTrue(history.repeated)

    def test_teacher_can_confirm_a_linked_learner(self):
        self.child.grade_confirmed_year = current_school_year() - 1
        self.child.save(update_fields=['grade_confirmed_year'])
        self.login_teacher()

        response = self.client.post(f'/confirm-grade/{self.child.id}', {'grade': '3'}, follow=True)
        self.assertEqual(response.status_code, 200)

        self.child.refresh_from_db()
        self.assertEqual(self.child.grade, 3)
        history = GradeHistory.objects.get(child=self.child, year=current_school_year())
        self.assertEqual(history.confirmed_by, GradeHistory.TEACHER)

    def test_parent_cannot_confirm_a_child_that_is_not_theirs(self):
        other_parent = Parent.objects.create(
            full_name='Other Parent', email='other-parent-gc@example.com',
            password=make_password('password123'), accepted_popia=True,
        )
        self.client.post('/login', {'role': 'parent', 'email': other_parent.email, 'password': 'password123'})
        self.child.grade_confirmed_year = current_school_year() - 1
        self.child.save(update_fields=['grade_confirmed_year'])

        self.client.post(f'/confirm-grade/{self.child.id}', {'grade': '4'})

        self.child.refresh_from_db()
        self.assertEqual(self.child.grade, 2)  # unchanged — access denied
        self.assertFalse(GradeHistory.objects.filter(child=self.child, year=current_school_year()).exists())

    def test_invalid_grade_is_rejected(self):
        self.child.grade_confirmed_year = current_school_year() - 1
        self.child.save(update_fields=['grade_confirmed_year'])
        self.login_parent()

        self.client.post(f'/confirm-grade/{self.child.id}', {'grade': '9'})

        self.child.refresh_from_db()
        self.assertEqual(self.child.grade, 2)
        self.assertTrue(self.child.needs_grade_confirmation())

    def test_unusual_grade_jump_gets_a_warning_but_still_applies(self):
        """A jump of more than one grade isn't blocked (rare but legitimate
        cases exist), but the parent/teacher gets a heads-up in case it was a
        mis-click rather than an intended multi-grade jump."""
        self.child.grade_confirmed_year = current_school_year() - 1
        self.child.save(update_fields=['grade_confirmed_year'])
        self.login_parent()

        response = self.client.post(f'/confirm-grade/{self.child.id}', {'grade': '4'}, follow=True)

        self.child.refresh_from_db()
        self.assertEqual(self.child.grade, 4)  # still applied
        warnings = [m for m in response.context['messages']]
        self.assertTrue(any('jump' in str(m).lower() for m in warnings))

    def test_normal_one_grade_promotion_gets_no_jump_warning(self):
        self.child.grade_confirmed_year = current_school_year() - 1
        self.child.save(update_fields=['grade_confirmed_year'])
        self.login_parent()

        response = self.client.post(f'/confirm-grade/{self.child.id}', {'grade': '3'}, follow=True)

        messages_text = [str(m).lower() for m in response.context['messages']]
        self.assertFalse(any('jump' in m for m in messages_text))


class GradeReminderEmailTests(TestCase):
    """Covers the send_grade_reminders management command: who gets emailed,
    grouping multiple children per parent, and not spamming on re-runs."""

    def setUp(self):
        self.parent = Parent.objects.create(
            full_name='Reminder Parent', email='reminder-parent@example.com',
            password=make_password('password123'), accepted_popia=True,
        )
        self.child = Child.objects.create(
            name='Reminder Kid', username='remindkid', grade=2,
            parent=self.parent, parent_email=self.parent.email,
            password=make_password('x'),
        )

    def backdate(self, child, years=1):
        child.grade_confirmed_year = current_school_year() - years
        child.save(update_fields=['grade_confirmed_year'])

    def test_no_email_when_already_confirmed(self):
        self.child.grade_confirmed_year = current_school_year()
        self.child.save(update_fields=['grade_confirmed_year'])
        call_command('send_grade_reminders')
        self.assertEqual(len(mail.outbox), 0)

    def test_emails_parent_when_confirmation_due(self):
        self.backdate(self.child)
        call_command('send_grade_reminders')
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, [self.parent.email])
        self.assertIn('Reminder Kid', sent.body)
        self.assertIn('/login', sent.body)
        # No one-click grade-change link — must not embed a confirm-grade URL.
        self.assertNotIn('/confirm-grade/', sent.body)

        self.child.refresh_from_db()
        self.assertTrue(self.child.reminder_already_sent_this_year())

    def test_does_not_resend_within_the_same_year(self):
        self.backdate(self.child)
        call_command('send_grade_reminders')
        call_command('send_grade_reminders')
        self.assertEqual(len(mail.outbox), 1)  # still just one email total

    def test_dry_run_sends_nothing(self):
        self.backdate(self.child)
        call_command('send_grade_reminders', '--dry-run')
        self.assertEqual(len(mail.outbox), 0)
        self.child.refresh_from_db()
        self.assertFalse(self.child.reminder_already_sent_this_year())

    def test_multiple_children_same_parent_get_one_combined_email(self):
        second_child = Child.objects.create(
            name='Second Kid', username='secondkid', grade=1,
            parent=self.parent, parent_email=self.parent.email,
            password=make_password('x'),
        )
        self.backdate(self.child)
        self.backdate(second_child)

        call_command('send_grade_reminders')

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn('Reminder Kid', body)
        self.assertIn('Second Kid', body)

    def test_confirming_stops_further_reminders(self):
        self.backdate(self.child)
        call_command('send_grade_reminders')
        self.assertEqual(len(mail.outbox), 1)

        self.child.record_grade_confirmation(3, confirmed_by=GradeHistory.PARENT, confirmed_by_name='Reminder Parent')

        # Confirmed for this year now — running the reminder job again must not re-email.
        call_command('send_grade_reminders')
        self.assertEqual(len(mail.outbox), 1)
