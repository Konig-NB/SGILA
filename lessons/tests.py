from django.test import Client, TestCase

from api.models import Child, Parent


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
