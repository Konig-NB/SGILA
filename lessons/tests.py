from django.test import Client, TestCase

from api.models import Child, Lesson, Parent, Progress, ReadingActivity
from api.reporting import rows_for_record


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
