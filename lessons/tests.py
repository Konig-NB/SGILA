import json

from django.test import TestCase

from api.models import Child, Lesson, Progress


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
