from django.db import migrations


OLD_PARENT_QUESTIONS = (
    'Q: How do I add my child? A: From your Parent dashboard, choose Add child and create a learner profile. Choose a username and password your child can use to sign in.',
    'Q: How do I connect my child to a teacher? A: Ask the teacher for their teacher code and enter it while adding the child. You can skip this step and link the class later using the code on the learner\'s grade page.',
    'Q: Where can I see my child\'s progress? A: Choose your child on the Parent dashboard to open their progress report. It includes lesson completion, stars, and assessment results.',
    'Q: Why is my child\'s grade asking to be confirmed? A: SGILA does not move learners up automatically. At the start of a school year, confirm the grade they are actually in. Keeping the same grade is an option if they are repeating it.',
    'Q: Why can\'t my child sign in? A: Check that they are using the learner username and password. Check the Parent dashboard for a paused profile or plan-access notice; reactivate the profile or update the plan there. If the password is forgotten, help your child use the correct account recovery option or contact support.',
    'Q: How do I change or recover my parent password? A: Use Forgot password on the Parent sign-in page and follow the email instructions. Check Spam or Junk if the message does not arrive.',
    'Q: My child is missing from the teacher dashboard. What can I check? A: Confirm the child\'s school and grade match the teacher profile, and check that the teacher code was entered correctly. Contact the teacher if the learner still does not appear.',
    'Q: Why is my child profile paused? A: Open the child\'s Report from your Parent dashboard to see whether the profile was paused manually or because the plan has reached its active-learner limit. Reactivate a manually paused profile there. For a plan limit, deactivate another learner or add a seat.',
    'Q: How do I add more active learner seats? A: Open your plan and choose Add a seat. Select the number of extra seats, review the monthly total, and continue to payment. Extra seats are available on eligible parent plans.',
    'Q: What parent plans are available? A: The plan page shows Individual for one child and Family for up to four children, with a 30-day trial. Review that page for current pricing and plan details.',
    'Q: How do I cancel my parent plan? A: Open the plan page and choose Cancel subscription, then follow the confirmation steps. Check the plan status on your dashboard afterward.',
    'Q: How do I message my child\'s teacher? A: Open Messages in the navigation, choose your child, and send a message to the linked teacher. Your child must be linked to that teacher with a class code.',
    'Q: What is included in my child\'s Report? A: Choose Report next to your child on the Parent dashboard to see completed lessons, assessment results, scores, and stars.',
    'Q: How do I pause or reactivate a child profile? A: Open Report beside the child on your Parent dashboard. Use Deactivate learner to pause access or Reactivate learner to restore it. Pausing a profile does not delete its learning records.',
)

PARENT_QUESTIONS = (
    'Q: How do I add my child? A: From your Parent dashboard, choose Add child and create a learner profile. Set a username and password your child can remember, and choose the correct school and grade.',
    'Q: How do I connect my child to a teacher? A: Ask the teacher for their teacher code and enter it while adding your child. You can also enter the code later from the learner\'s grade page. If the class-code box is not shown, the profile is already linked to a class.',
    'Q: How does my child sign in and find stories? A: Choose Learner sign in and use the username and password you created. After signing in, your child can open the stories listed on their grade page. Check the profile grade if the expected stories are missing.',
    'Q: How can I help my child choose an activity? A: Open a story from the grade page. The activity menu shows the choices available for that lesson and grade, such as story questions, picture matching, spelling, pronunciation, vocabulary, sequencing, or prediction.',
    'Q: Can my child continue a lesson later? A: If your child saves their place when pausing an activity, reopen that lesson and choose Continue where I paused. Otherwise, choose an activity from the lesson menu to continue.',
    'Q: How are stars earned, and where can I see them? A: A completed lesson earns 1 star below 70%, 2 stars from 70%, and 3 stars from 90%. The grade page shows total stars and completed lessons; the Report shows scores and assessment results.',
    'Q: When can my child unlock a personal story? A: Explore more stories unlocks after your child masters every workbook story for their grade with at least 95%. If a personal story already exists, that story must also be mastered before another unlocks.',
    'Q: What should we try if a story or its audio does not work? A: Check the internet connection and device volume, reload the page, and try again. For speaking activities, allow microphone access in the browser. Ask your child to try again, or contact the teacher if it continues.',
    'Q: Where can I review my child\'s learning progress? A: Choose Report next to your child on the Parent dashboard. It shows completed lessons, assessment results, scores, and stars. Teachers can review the linked learner from their dashboard too.',
    'Q: Why does my child need a grade confirmation? A: SGILA does not move learners up automatically. At the start of a school year, confirm the grade your child is actually in. Keeping the same grade is an option if your child is repeating it.',
    'Q: Why can\'t my child sign in? A: Check the learner username and password, then check the Parent dashboard for a paused profile or plan-access notice. Reactivate a manually paused profile there. If your child forgot their password, use the account recovery instructions or contact support.',
    'Q: How do I reset my parent password? A: Use Forgot password on the Parent sign-in page and follow the email instructions. Check Spam or Junk if the reset message does not arrive.',
    'Q: Why is my child missing from the teacher dashboard? A: Confirm the child\'s school and grade match the teacher profile, and verify that the teacher code was entered correctly. The learner must be linked to the teacher before appearing on their dashboard or in Messages.',
    'Q: How do I message my child\'s teacher? A: Open Messages in the navigation, choose your child, and send a message to the linked teacher. If your child is not listed, link the learner profile using the teacher code first.',
    'Q: How do I pause or reactivate my child\'s profile? A: Choose Report beside your child on the Parent dashboard. Use Deactivate learner to pause sign-in access or Reactivate learner to restore it. Pausing a profile does not delete its learning records.',
    'Q: Why is learner access paused, and how do I add a seat? A: If the plan has reached its active-learner limit, deactivate another learner or open your plan and choose Add a seat. Select extra seats, review the monthly total, and continue to payment.',
    'Q: Which parent plans are available, and how do I cancel? A: The plan page shows Individual for one child and Family for up to four children, with a 30-day trial. Review that page for current pricing. To cancel, choose Cancel subscription on the plan page and follow the confirmation steps.',
)


def merge_parent_questions(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias
    article = HelpArticle.objects.using(database).filter(
        slug='parent-child-profiles-and-progress',
    ).first()
    if article:
        article.content = '\n\n'.join(PARENT_QUESTIONS)
        article.save(using=database, update_fields=['content'])


def restore_parent_questions(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias
    article = HelpArticle.objects.using(database).filter(
        slug='parent-child-profiles-and-progress',
    ).first()
    if article:
        article.content = '\n\n'.join(OLD_PARENT_QUESTIONS)
        article.save(using=database, update_fields=['content'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0033_feedback'),
    ]

    operations = [
        migrations.RunPython(merge_parent_questions, restore_parent_questions),
    ]