from django.db import migrations


GUIDES = (
    {
        'category': {
            'name': 'Learner help',
            'slug': 'learner-help',
            'description': 'Stories, activities, progress, and learner accounts',
            'order': 4,
        },
        'article': {
            'title': 'Learner questions about stories and activities',
            'slug': 'learner-stories-and-activities',
            'audience': 'learner',
            'is_kid_friendly': True,
            'content': (
                'Q: How do I sign in? A: Choose Learner sign in and enter the username '
                'and password your parent or teacher gave you. If you do not know them, '
                'ask that grown-up for help.\n\n'
                'Q: Where do I find my stories? A: After you sign in, open a story on '
                'your grade page. If the grade looks wrong, ask your parent or teacher '
                'to check your profile.\n\n'
                'Q: How do I do the activities? A: Open a story and choose an activity '
                'when the activity choices appear. Read each question and follow the '
                'instructions on the screen.\n\n'
                'Q: Where can I see my stars and finished lessons? A: Your grade page '
                'shows your stars and the number of lessons you have completed. Your '
                'parent or teacher can also see your progress.\n\n'
                'Q: How do I join my teacher\'s class? A: Ask your teacher or parent '
                'for the class code. Enter it in the Have a class code box on your '
                'grade page, then choose Link class. Ask a grown-up if the code does '
                'not work.\n\n'
                'Q: A story or sound is not working. What should I do? A: Check that '
                'your device is online, reload the page, and try again. Ask a grown-up '
                'to check the device sound or browser microphone permission if an '
                'activity needs it.\n\n'
                'Q: I forgot my password. Can I reset it? A: Ask your parent or '
                'teacher to help. Learner profiles use sign-in details managed by an '
                'adult.'
            ),
        },
    },
    {
        'category': {
            'name': 'Parent help',
            'slug': 'parent-help',
            'description': 'Child profiles, learning progress, and family access',
            'order': 5,
        },
        'article': {
            'title': 'Parent questions about child profiles and progress',
            'slug': 'parent-child-profiles-and-progress',
            'audience': 'parent',
            'is_kid_friendly': False,
            'content': (
                'Q: How do I add my child? A: From your Parent dashboard, choose Add '
                'child and create a learner profile. Choose a username and password '
                'your child can use to sign in.\n\n'
                'Q: How do I connect my child to a teacher? A: Ask the teacher for '
                'their teacher code and enter it while adding the child. You can skip '
                'this step and link the class later using the code on the learner\'s '
                'grade page.\n\n'
                'Q: Where can I see my child\'s progress? A: Choose your child on the '
                'Parent dashboard to open their progress report. It includes lesson '
                'completion, stars, and assessment results.\n\n'
                'Q: Why is my child\'s grade asking to be confirmed? A: SGILA does not '
                'move learners up automatically. At the start of a school year, confirm '
                'the grade they are actually in. Keeping the same grade is an option '
                'if they are repeating it.\n\n'
                'Q: Why can\'t my child sign in? A: Check that they are using the '
                'learner username and password. Check the Parent dashboard for a '
                'paused profile or plan-access notice; reactivate the profile or update '
                'the plan there. If the password is forgotten, help your child use the '
                'correct account recovery option or contact support.\n\n'
                'Q: How do I change or recover my parent password? A: Use Forgot '
                'password on the Parent sign-in page and follow the email instructions. '
                'Check Spam or Junk if the message does not arrive.\n\n'
                'Q: My child is missing from the teacher dashboard. What can I check? '
                'A: Confirm the child\'s school and grade match the teacher profile, '
                'and check that the teacher code was entered correctly. Contact the '
                'teacher if the learner still does not appear.'
            ),
        },
    },
    {
        'category': {
            'name': 'Teacher help',
            'slug': 'teacher-help',
            'description': 'Teacher codes, learner access, and class progress',
            'order': 6,
        },
        'article': {
            'title': 'Teacher questions about class codes and progress',
            'slug': 'teacher-class-codes-and-progress',
            'audience': 'teacher',
            'is_kid_friendly': False,
            'content': (
                'Q: Where do I find my teacher code? A: It is shown in the Teacher '
                'dashboard code panel. Share it with parents so they can enter it '
                'when creating a learner profile.\n\n'
                'Q: A learner is not appearing on my dashboard. What should I check? '
                'A: Confirm the learner\'s school and grade match your teacher profile. '
                'Ask the parent to check that your teacher code was entered correctly. '
                'A learner can also enter the class code from their grade page.\n\n'
                'Q: What do the dashboard numbers show? A: The summary shows learner '
                'count, class average, learners needing support, and completed lessons. '
                'Open a grade section to review learners and their latest completed '
                'lesson.\n\n'
                'Q: How do I confirm a learner\'s grade for a new school year? A: Use '
                'the grade-confirmation controls on your dashboard. Choose the '
                'suggested grade, keep the current grade for a learner who is repeating, '
                'or choose a different grade. SGILA does not promote learners '
                'automatically.\n\n'
                'Q: Can I assign a custom lesson from the dashboard? A: The dashboard '
                'shows progress; it does not provide custom lesson assignment controls. '
                'Learners see lessons for their grade.\n\n'
                'Q: I cannot sign in or my account is inactive. What should I do? A: '
                'Use Forgot password on the Teacher sign-in page to recover your '
                'password. If the account was deactivated, sign in and follow the '
                'reactivation steps. Check Spam or Junk for verification or reactivation '
                'emails; see the Email delivery guides if they do not arrive.'
            ),
        },
    },
)


def seed_role_guides(apps, schema_editor):
    HelpCategory = apps.get_model('api', 'HelpCategory')
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias

    for guide in GUIDES:
        category, _created = HelpCategory.objects.using(database).get_or_create(
            slug=guide['category']['slug'],
            defaults=guide['category'],
        )
        HelpArticle.objects.using(database).get_or_create(
            slug=guide['article']['slug'],
            defaults={**guide['article'], 'category_id': category.pk},
        )


def remove_role_guides(apps, schema_editor):
    HelpCategory = apps.get_model('api', 'HelpCategory')
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias

    HelpArticle.objects.using(database).filter(
        slug__in=[guide['article']['slug'] for guide in GUIDES],
    ).delete()
    HelpCategory.objects.using(database).filter(
        slug__in=[guide['category']['slug'] for guide in GUIDES],
        articles__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0030_seed_email_help_guides'),
    ]

    operations = [
        migrations.RunPython(seed_role_guides, remove_role_guides),
    ]