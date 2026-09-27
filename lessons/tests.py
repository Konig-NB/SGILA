import json

from django.test import Client, TestCase

from api.models import Child, Lesson, Parent, Progress, ReadingActivity
from api.reporting import rows_for_record
from lessons.views import activity_choices_for


class GradeThreeActivityResultsTests(TestCase):
	def setUp(self):
		self.child = Child.objects.create(
			name='Thato',
			age=9,
			grade=3,
			parent_email='thato@example.com',
			password='hash',
		)
		self.lesson = Lesson.objects.create(title='Mandu\'s Secret Diary', grade=3)
		session = self.client.session
		session['account_role'] = 'learner'
		session['account_id'] = self.child.id
		session['account_name'] = self.child.name
		session['child_id'] = self.child.id
		session['child_name'] = self.child.name
		session['child_grade'] = self.child.grade
		session.save()

	def test_activity_completion_saves_breakdown_for_results_page(self):
		activity_scores = [
			{'number': 1, 'score': 4, 'total': 5},
			{'number': 2, 'score': 3, 'total': 4},
			{'number': 3, 'score': 5, 'total': 5},
			{'number': 4, 'score': 2, 'total': 4},
			{'number': 5, 'score': 4, 'total': 4},
			{'number': 6, 'score': 3, 'total': 5},
		]
		response = self.client.post(
			f'/lessons/{self.lesson.id}/activities/complete',
			data=json.dumps({'activity_scores': activity_scores}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		record = Progress.objects.get(child=self.child, lesson=self.lesson)
		self.assertEqual((record.total_score, record.total_possible), (21, 27))
		grade_home = self.client.get('/grade/3')

		self.assertContains(grade_home, 'Completed')
		for activity_label in (
			'Activity 1: Comprehension Questions',
			'Activity 2: Sequencing',
			'Activity 3: True or False',
			'Activity 4: Word Detective',
			'Activity 5: Spelling Questions',
			'Activity 6: Word Balloon Pop',
		):
			with self.subTest(activity=activity_label):
				self.assertContains(grade_home, activity_label)

		results = self.client.get(f'/lessons/{self.lesson.id}/results')

		self.assertEqual(results.status_code, 200)
		for label, score in (
			('Comprehension check', '4/5'),
			('Picture match', '3/4'),
			('True or False', '5/5'),
			('Word detective', '2/4'),
			('Listen and spell', '4/4'),
			('Word Balloon Pop', '3/5'),
		):
			with self.subTest(activity=label):
				self.assertContains(results, label)
				self.assertContains(results, score)


class GradeAccessTests(TestCase):
	def test_learner_cannot_open_another_grade(self):
		parent = Parent.objects.create(
			full_name='Test Parent',
			email='grade-access-parent@example.com',
			password='not-a-real-password',
		)
		child = Child.objects.create(
			parent=parent,
			name='Sipho Dlamini',
			username='SiphoDlamini',
			grade=1,
			parent_email=parent.email,
			password='not-a-real-password',
		)
		client = Client()
		session = client.session
		session['account_role'] = 'learner'
		session['account_id'] = child.id
		session['child_id'] = child.id
		session['child_grade'] = child.grade
		session.save()

		response = client.get('/grade/2')

		self.assertRedirects(response, '/grade/1')


class ActivityMenuLabelTests(TestCase):
	def test_grade_four_activity_labels_are_descriptive_and_unique(self):
		lesson = Lesson.objects.create(title='Popup Labels', grade=4)
		for order, activity_type in enumerate([
			ReadingActivity.MULTIPLE_CHOICE,
			ReadingActivity.MATCHING,
			ReadingActivity.MATCHING,
		], start=1):
			ReadingActivity.objects.create(
				lesson=lesson,
				activity_type=activity_type,
				skill='vocabulary_in_context',
				question='Activity question',
				order=order,
			)

		labels = [choice['label'] for choice in activity_choices_for(lesson)]

		self.assertEqual(len(labels), len(set(labels)))
		self.assertIn('Story Choices: Pick the Best Answer', labels)
		self.assertIn('Matching: Connect Story Words - Part 2', labels)


class ActivityScoreReportingTests(TestCase):
	def test_missing_activity_is_excluded_from_stored_breakdown(self):
		parent = Parent.objects.create(
			full_name='Score Parent',
			email='score-parent@example.com',
			password='not-a-real-password',
		)
		child = Child.objects.create(
			parent=parent,
			name='Score Learner',
			username='ScoreLearner',
			grade=4,
			parent_email=parent.email,
			password='not-a-real-password',
		)
		lesson = Lesson.objects.create(title='Story Without Sequencing', grade=4)
		ReadingActivity.objects.create(
			lesson=lesson,
			activity_type=ReadingActivity.MULTIPLE_CHOICE,
			skill='literal_comprehension',
			question='What happened?',
		)
		record = Progress.objects.create(
			child=child,
			lesson=lesson,
			assessment_scores={
				'reading': {'score': 2, 'total': 2},
				'sequencing': {'score': 0, 'total': 1},
			},
			total_score=2,
			total_possible=3,
		)

		rows = rows_for_record(record)

		self.assertEqual(rows, [{
			'key': 'reading',
			'label': 'Reading',
			'initial': 'R',
			'tip': 'Re-read the story and use its details to answer questions.',
			'score': 2,
			'total': 2,
			'pct': 100,
		}])
