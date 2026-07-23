import json

from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase

from api.models import (
    Child,
    ComprehensionQuestion,
    Lesson,
    Parent,
    PronunciationWord,
    Progress,
    SpellingActivity,
    StoryPage,
    Teacher,
    TeacherClass,
    VisualActivityItem,
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

    def test_learner_can_register_and_reach_lesson_flow(self):
        response = self.client.post("/register", {
            "role": "learner",
            "child_name": "Sipho",
            "age": 7,
            "grade": 1,
            "school_name": "Thuthuka Primary",
            "parent_email": "sipho@example.com",
            "password": "password123",
        })
        self.assertRedirects(response, "/grade/1")
        self.assertEqual(Child.objects.count(), 1)

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
        self.assertRedirects(parent_response, "/parent/dashboard")
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
            "username": "lethu_m",
            "first_name": "Lethu",
            "last_name": "Mokoena",
            "age": 7,
            "grade": 1,
            "school_name": "",
            "class_code": teacher_class.class_code,
            "password": "password123",
        })
        self.assertRedirects(response, "/parent/dashboard")
        child = Child.objects.get(username="lethu_m")
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

    def test_parent_dashboard_congratulates_perfect_work(self):
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

        response = self.client.get("/parent/dashboard")
        self.assertContains(response, "Congratulations!")
        self.assertContains(response, "got everything right")

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
        self.assertEqual(self.client.get(f"/api/progress/{child.id}").status_code, 403)

        self.sign_in_child(child)
        self.assertEqual(self.client.get(f"/dashboard/{child.id}").status_code, 200)
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
        self.assertContains(story_response, "Answer questions")
        self.assertEqual(visual_response.status_code, 200)
        self.assertContains(visual_response, "No visual matching cards have been added yet.")
        self.assertContains(visual_response, "Continue")
