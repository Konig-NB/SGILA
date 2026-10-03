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
	def test_grade_one_activity_labels_match_the_story_groups(self):
		lesson = Lesson.objects.create(title='Grade One Story', grade=1)
		for order, group_number, activity_type, skill, question in [
			(1, 1, ReadingActivity.CLOZE, 'spelling', 'Complete the word'),
			(2, 1, ReadingActivity.CLOZE, 'spelling', 'Complete the word'),
			(3, 1, ReadingActivity.CLOZE, 'spelling', 'Complete the word'),
			(4, 2, ReadingActivity.MULTIPLE_CHOICE, 'literal_comprehension', 'Picture question'),
			(5, 2, ReadingActivity.MULTIPLE_CHOICE, 'literal_comprehension', 'Picture question'),
			(6, 2, ReadingActivity.MULTIPLE_CHOICE, 'literal_comprehension', 'Picture question'),
			(7, 3, ReadingActivity.MULTIPLE_CHOICE, 'vocabulary_in_context', 'Sentence question'),
			(8, 3, ReadingActivity.MULTIPLE_CHOICE, 'vocabulary_in_context', 'Sentence question'),
			(9, 3, ReadingActivity.MULTIPLE_CHOICE, 'vocabulary_in_context', 'Sentence question'),
		]:
			ReadingActivity.objects.create(
				lesson=lesson,
				activity_type=activity_type,
				skill=skill,
				question=question,
				group_number=group_number,
				order=order,
			)

		choices = activity_choices_for(lesson)
		self.assertEqual(
			[choice['label'] for choice in choices],
			[
				'Read the Story',
				'Spelling - Fill in the Blank',
				'Comprehension - Multiple Choice',
				'Vocabulary - Multiple Choice',
			],
		)
		self.assertEqual(
			[choice['url'] for choice in choices],
			[
				f'/lessons/{lesson.id}/story',
				f'/lessons/{lesson.id}/questions?activity_index=0',
				f'/lessons/{lesson.id}/questions?activity_index=3',
				f'/lessons/{lesson.id}/questions?activity_index=6',
			],
		)

	def test_grade_two_activity_labels_match_the_story_groups(self):
		lesson = Lesson.objects.create(title='Grade Two Story', grade=2)
		for order, group_number, activity_type, skill, question in [
			(1, 1, ReadingActivity.MULTIPLE_CHOICE, 'literal_comprehension', 'Comprehension question'),
			(2, 2, ReadingActivity.MATCHING, 'literal_comprehension', 'Match it question'),
			(3, 3, ReadingActivity.MULTIPLE_CHOICE, 'vocabulary_in_context', 'Visual match question'),
			(4, 4, ReadingActivity.CLOZE, 'spelling', 'Spelling question'),
			(5, 5, ReadingActivity.CLOZE, 'literal_comprehension', 'Fix mistake question'),
		]:
			ReadingActivity.objects.create(
				lesson=lesson,
				activity_type=activity_type,
				skill=skill,
				question=question,
				group_number=group_number,
				order=order,
			)

		choices = activity_choices_for(lesson)
		self.assertEqual(
			[choice['label'] for choice in choices],
			[
				'Read the Story',
				'Comprehension Questions',
				'Match It!',
				'Visual Matching',
				'Spelling',
				'Fix the Mistake',
			],
		)
		self.assertEqual(
			[choice['url'] for choice in choices],
			[
				f'/lessons/{lesson.id}/story',
				f'/lessons/{lesson.id}/questions?activity_index=0',
				f'/lessons/{lesson.id}/questions?activity_index=1',
				f'/lessons/{lesson.id}/questions?activity_index=2',
				f'/lessons/{lesson.id}/questions?activity_index=3',
				f'/lessons/{lesson.id}/questions?activity_index=4',
			],
		)

	def test_grade_three_activity_labels_match_the_story_sections(self):
		lesson = Lesson.objects.create(title='Grade Three Story', grade=3)

		choices = activity_choices_for(lesson)
		self.assertEqual(
			[choice['label'] for choice in choices],
			[
				'Read the Story',
				'Comprehension Questions - Remember the story',
				'Sequencing - Put events in order',
				'True or False - Think carefully',
				'Word Detective - Find the missing words',
				'Spelling Questions - Build the story words',
				'Word Balloon Pop',
			],
		)
		self.assertEqual(
			[choice['url'] for choice in choices],
			[
				f'/lessons/{lesson.id}/story',
				f'/lessons/{lesson.id}/activities?activity_index=0',
				f'/lessons/{lesson.id}/activities?activity_index=1',
				f'/lessons/{lesson.id}/activities?activity_index=2',
				f'/lessons/{lesson.id}/activities?activity_index=3',
				f'/lessons/{lesson.id}/activities?activity_index=4',
				f'/lessons/{lesson.id}/activities?activity_index=5',
			],
		)

	def test_grade_three_pause_saves_resume_url_and_score(self):
		parent = Parent.objects.create(
			full_name='Pause Parent',
			email='pause-parent@example.com',
			password='not-a-real-password',
		)
		child = Child.objects.create(
			parent=parent,
			name='Grade 3 Learner',
			username='Grade3PauseLearner',
			grade=3,
			parent_email=parent.email,
			password='not-a-real-password',
		)
		lesson = Lesson.objects.create(title='Paused Grade Three Story', grade=3)
		client = Client()
		session = client.session
		session['account_role'] = 'learner'
		session['account_id'] = child.id
		session['child_id'] = child.id
		session['child_grade'] = child.grade
		session.save()

		response = client.post(
			f'/lessons/{lesson.id}/activity-pause',
			json.dumps({
				'resume_url': f'/lessons/{lesson.id}/activities?activity_index=3&question_index=2',
				'score': {'score': 2, 'total': 5},
			}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload['score'], 2)
		self.assertEqual(payload['total'], 5)
		refreshed_child = Child.objects.get(pk=child.pk)
		self.assertEqual(
			refreshed_child.paused_activities[str(lesson.id)]['url'],
			f'/lessons/{lesson.id}/activities?activity_index=3&question_index=2',
		)
		self.assertEqual(refreshed_child.paused_activities[str(lesson.id)]['score'], 2)
		self.assertEqual(refreshed_child.paused_activities[str(lesson.id)]['total'], 5)

	def test_grade_four_activity_labels_match_the_story_pages(self):
		lesson = Lesson.objects.create(title='Grade Four Story', grade=4)
		for model, factory in [
			('vocabulary_questions', lambda: __import__('api.models', fromlist=['VocabularyQuestion']).VocabularyQuestion.objects.create(lesson=lesson, word='precious', option_1='valuable', option_2='quick', option_3='slow', correct_answer='valuable')),
			('sequencing_activities', lambda: __import__('api.models', fromlist=['SequencingActivity']).SequencingActivity.objects.create(lesson=lesson, ordered_events='One|Two|Three', instruction='Put events in order')),
			('inference_questions', lambda: __import__('api.models', fromlist=['InferenceQuestion']).InferenceQuestion.objects.create(lesson=lesson, question='Why?', option_1='A', option_2='B', option_3='C', option_4='D', correct_answer='A')),
			('prediction_questions', lambda: __import__('api.models', fromlist=['PredictionQuestion']).PredictionQuestion.objects.create(lesson=lesson, stop_point_text='Stop', question='What next?', option_1='A', option_2='B', option_3='C', option_4='D', correct_answer='A')),
			('feelings_questions', lambda: __import__('api.models', fromlist=['FeelingsQuestion']).FeelingsQuestion.objects.create(lesson=lesson, question='How did they feel?', option_1='Happy', option_2='Angry', option_3='Sad', option_4='Excited', correct_answer='Happy')),
			('cause_effect_pairs', lambda: __import__('api.models', fromlist=['CauseEffectPair']).CauseEffectPair.objects.create(lesson=lesson, cause='Rain fell', effect='The ground was wet', order=1)),
			('theme_questions', lambda: __import__('api.models', fromlist=['ThemeQuestion']).ThemeQuestion.objects.create(lesson=lesson, question='What is the theme?', option_1='A', option_2='B', option_3='C', option_4='D', correct_answer='A')),
		]:
			factory()

		choices = activity_choices_for(lesson)
		self.assertEqual(
			[choice['label'] for choice in choices],
			[
				'Read the Story',
				'Vocabulary: Explore New Words',
				'Sequencing: Order Events',
				'Inference: Read Between the Lines',
				'Prediction: Think Ahead',
				'Feelings: Understand Characters',
				'Cause and Effect: Follow the Story',
				'Main Lesson: Find the Big Idea',
			],
		)
		self.assertEqual(
			[choice['url'] for choice in choices],
			[
				f'/lessons/{lesson.id}/story',
				f'/lessons/{lesson.id}/vocabulary',
				f'/lessons/{lesson.id}/sequencing',
				f'/lessons/{lesson.id}/inference',
				f'/lessons/{lesson.id}/prediction',
				f'/lessons/{lesson.id}/feelings',
				f'/lessons/{lesson.id}/cause-effect',
				f'/lessons/{lesson.id}/theme',
			],
		)

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

	def test_grade_three_partial_completion_keeps_activity_breakdown(self):
		parent = Parent.objects.create(
			full_name='Partial Grade Three Parent',
			email='partial-grade-three-parent@example.com',
			password='not-a-real-password',
		)
		child = Child.objects.create(
			parent=parent,
			name='Partial Grade Three Learner',
			username='PartialGradeThreeLearner',
			grade=3,
			parent_email=parent.email,
			password='not-a-real-password',
		)
		lesson = Lesson.objects.create(title='Partial Grade Three Story', grade=3)
		client = Client()
		session = client.session
		session['account_role'] = 'learner'
		session['account_id'] = child.id
		session['child_id'] = child.id
		session['child_grade'] = child.grade
		session.save()

		first_response = client.post(
			f'/lessons/{lesson.id}/activities/complete',
			data=json.dumps({
				'total_score': 4,
				'total_possible': 5,
				'activity_scores': [{'number': '1', 'score': 4, 'total': 5}],
			}),
			content_type='application/json',
		)
		self.assertEqual(first_response.status_code, 200)

		response = client.post(
			f'/lessons/{lesson.id}/activities/complete',
			data=json.dumps({
				'total_score': 2,
				'total_possible': 3,
				'activity_scores': [{'number': '6', 'score': 2, 'total': 3}],
			}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {'completed': True})
		record = Progress.objects.get(child=child, lesson=lesson)
		self.assertEqual(
			{row['key']: (row['score'], row['total']) for row in rows_for_record(record)},
			{
				'grade3_comprehension_check': (4, 5),
				'grade3_word_balloon': (2, 3),
			},
		)
		self.assertEqual((record.total_score, record.total_possible), (6, 8))

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
