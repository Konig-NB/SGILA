import json

from django.test import Client, TestCase

from api.models import Child, Lesson, Parent, Progress, ReadingActivity
from api.reporting import rows_for_record
from lessons.views import activity_choices_for


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
	def test_grade_three_completion_marks_appear_in_the_report(self):
		parent = Parent.objects.create(
			full_name='Grade Three Parent',
			email='grade-three-parent@example.com',
			password='not-a-real-password',
		)
		child = Child.objects.create(
			parent=parent,
			name='Grade Three Learner',
			username='GradeThreeLearner',
			grade=3,
			parent_email=parent.email,
			password='not-a-real-password',
		)
		lesson = Lesson.objects.create(title='Grade Three Story', grade=3)
		client = Client()
		session = client.session
		session['account_role'] = 'learner'
		session['account_id'] = child.id
		session['child_id'] = child.id
		session['child_grade'] = child.grade
		session.save()
		activity_scores = [
			{'number': str(number), 'score': score, 'total': 5}
			for number, score in enumerate([4, 3, 2, 5, 1, 4], start=1)
		]

		response = client.post(
			f'/lessons/{lesson.id}/activities/complete',
			data=json.dumps({
				'total_score': 19,
				'total_possible': 30,
				'activity_scores': activity_scores,
			}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		record = Progress.objects.get(child=child, lesson=lesson)
		self.assertEqual(
			{row['key']: row['score'] for row in rows_for_record(record)},
			{
				'grade3_comprehension_check': 4,
				'grade3_visual_match': 3,
				'grade3_true_false': 2,
				'grade3_word_detective': 5,
				'grade3_listen_spell': 1,
				'grade3_word_balloon': 4,
			},
		)

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
