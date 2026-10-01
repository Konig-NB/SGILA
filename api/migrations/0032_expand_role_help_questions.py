from django.db import migrations


ROLE_QUESTIONS = {
    'learner-stories-and-activities': (
        'Q: How do I choose an activity? A: Open a lesson on your grade page and choose one of the activities shown. The choices depend on your grade and the lesson.',
        'Q: Can I continue a lesson where I stopped? A: If you saved your place while pausing an activity, open that lesson again and choose Continue where I paused. If you do not see that option, choose an activity from the lesson menu.',
        'Q: How many stars can I earn for a lesson? A: A completed lesson earns 1 star for a score below 70%, 2 stars for a score of 70% or more, and 3 stars for a score of 90% or more.',
        'Q: When can I make a story just for me? A: After you master every workbook story for your grade with a score of at least 95%, Explore more stories becomes available. If you already have a personal story, you need to master that one too before another can unlock.',
        'Q: Why can I not see the class-code box? A: The box appears only when your learner profile is not already linked to a class. If you need to change classes, ask your parent or teacher for help.',
        'Q: What kinds of activities are available? A: Each lesson has its own choices. You may see story questions, picture matching, spelling, pronunciation, vocabulary, sequencing, prediction, or other activities. Choose from the menu shown for your lesson.',
        'Q: The story voice will not play. What can I do? A: Press Play story voice, check your device volume, and make sure your browser is allowed to play audio. Reload the page and try again, or ask a grown-up to help.',
    ),
    'parent-child-profiles-and-progress': (
        'Q: Why is my child profile paused? A: Open the child\'s Report from your Parent dashboard to see whether the profile was paused manually or because the plan has reached its active-learner limit. Reactivate a manually paused profile there. For a plan limit, deactivate another learner or add a seat.',
        'Q: How do I add more active learner seats? A: Open your plan and choose Add a seat. Select the number of extra seats, review the monthly total, and continue to payment. Extra seats are available on eligible parent plans.',
        'Q: What parent plans are available? A: The plan page shows Individual for one child and Family for up to four children, with a 30-day trial. Review that page for current pricing and plan details.',
        'Q: How do I cancel my parent plan? A: Open the plan page and choose Cancel subscription, then follow the confirmation steps. Check the plan status on your dashboard afterward.',
        'Q: How do I message my child\'s teacher? A: Open Messages in the navigation, choose your child, and send a message to the linked teacher. Your child must be linked to that teacher with a class code.',
        'Q: What is included in my child\'s Report? A: Choose Report next to your child on the Parent dashboard to see completed lessons, assessment results, scores, and stars.',
        'Q: How do I pause or reactivate a child profile? A: Open Report beside the child on your Parent dashboard. Use Deactivate learner to pause access or Reactivate learner to restore it. Pausing a profile does not delete its learning records.',
    ),
    'teacher-class-codes-and-progress': (
        'Q: How do I open a learner\'s full report? A: Find the learner in the matching grade section of your Teacher dashboard and choose Report. The report shows lesson progress, results, and stars.',
        'Q: What does Need support mean on my dashboard? A: A learner is flagged as needing support when they have assessment results and their average is below 70%. Open their Report to review the results.',
        'Q: How do I message a learner\'s parent? A: Open Messages in the navigation and choose the learner. You can message the parent linked to that learner.',
        'Q: How do learners join my class? A: Share your teacher code with the parent. They can enter it while adding a learner, or the learner can enter the class code on their grade page if they are not already linked.',
        'Q: What happens if I deactivate my teacher account? A: You will be signed out and lose access to your classes until you reactivate. Your teacher profile and class records remain stored. Learners may be flagged as needing a new teacher while your account is inactive.',
        'Q: Where can I find school or district plans? A: Open the plan page from your account. Teacher accounts see the enterprise package information for schools and districts; contact SGILA for help choosing a package.',
    ),
}


def add_questions(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias

    for slug, questions in ROLE_QUESTIONS.items():
        article = HelpArticle.objects.using(database).filter(slug=slug).first()
        if not article:
            continue
        paragraphs = article.content.split('\n\n')
        missing = [question for question in questions if question not in paragraphs]
        if missing:
            article.content = '\n\n'.join([article.content.rstrip(), *missing])
            article.save(using=database, update_fields=['content'])


def remove_questions(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias

    for slug, questions in ROLE_QUESTIONS.items():
        article = HelpArticle.objects.using(database).filter(slug=slug).first()
        if not article:
            continue
        paragraphs = [
            paragraph
            for paragraph in article.content.split('\n\n')
            if paragraph not in questions
        ]
        article.content = '\n\n'.join(paragraphs)
        article.save(using=database, update_fields=['content'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_seed_role_help_guides'),
    ]

    operations = [
        migrations.RunPython(add_questions, remove_questions),
    ]