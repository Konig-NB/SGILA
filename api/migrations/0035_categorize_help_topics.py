import re

from django.db import migrations


GUIDES = {
    'learner-stories-and-activities': {
        'title': 'Learner questions about stories and activities',
        'category': 'learner-help',
    },
    'parent-child-profiles-and-progress': {
        'title': 'Parent questions about child profiles and progress',
        'category': 'parent-help',
    },
    'teacher-class-codes-and-progress': {
        'title': 'Teacher questions about class codes and progress',
        'category': 'teacher-help',
    },
}

CATEGORIES = (
    {
        'name': 'Getting started',
        'slug': 'getting-started-guides',
        'description': 'Creating a learner profile and getting set up',
        'order': 1,
    },
    {
        'name': 'Accounts and sign-in',
        'slug': 'account-access',
        'description': 'Passwords, sign-in, and learner account access',
        'order': 2,
    },
    {
        'name': 'Learning and activities',
        'slug': 'learning-activities',
        'description': 'Stories, lessons, and learning activities',
        'order': 3,
    },
    {
        'name': 'Progress and reports',
        'slug': 'progress-reports',
        'description': 'Stars, scores, dashboards, and learner reports',
        'order': 4,
    },
    {
        'name': 'Classes and connections',
        'slug': 'class-connections',
        'description': 'Class codes and connecting learners, parents, and teachers',
        'order': 5,
    },
    {
        'name': 'Plans and billing',
        'slug': 'plans-billing',
        'description': 'Plans, seats, subscriptions, and school packages',
        'order': 6,
    },
    {
        'name': 'Audio and troubleshooting',
        'slug': 'audio-troubleshooting',
        'description': 'Audio playback and activity technical issues',
        'order': 7,
    },
)


def category_for_question(question, category_ids):
    text = question.lower()
    if any(term in text for term in (
        'add my child',
        'sign in and find stories',
        'grade asking to be confirmed',
        'grade confirmation',
        'confirm a learner',
    )):
        return category_ids['getting-started-guides']
    if any(term in text for term in ('plan', 'seat', 'subscription', 'cancel', 'district')):
        return category_ids['plans-billing']
    if any(term in text for term in ('audio', 'sound', 'voice', 'microphone')):
        return category_ids['audio-troubleshooting']
    if any(term in text for term in ('progress', 'report', 'star', 'score', 'need support', 'dashboard numbers')):
        return category_ids['progress-reports']
    if any(term in text for term in (
        'class',
        'teacher code',
        'teacher dashboard',
        'connect my child to a teacher',
        'learner is not appearing on my dashboard',
        'message my child',
        'message a learner',
        'join my teacher',
    )):
        return category_ids['class-connections']
    if any(term in text for term in ('sign in', 'password', 'account', 'profile paused', 'reactivate')):
        return category_ids['account-access']
    return category_ids['learning-activities']


def categorize_help_topics(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    HelpCategory = apps.get_model('api', 'HelpCategory')
    database = schema_editor.connection.alias

    category_ids = {}
    for category_data in CATEGORIES:
        category, _created = HelpCategory.objects.using(database).get_or_create(
            slug=category_data['slug'],
            defaults=category_data,
        )
        category_ids[category.slug] = category.pk

    email_category = HelpCategory.objects.using(database).filter(slug='email-delivery').first()
    if email_category:
        email_category.order = 8
        email_category.save(using=database, update_fields=['order'])

    for guide_slug, guide_data in GUIDES.items():
        article = HelpArticle.objects.using(database).filter(slug=guide_slug).first()
        if not article:
            continue

        paragraphs = article.content.split('\n\n')
        topics = []
        for paragraph in paragraphs:
            match = re.match(r'^Q:\s*(.*?)\s+A:\s*([\s\S]*)$', paragraph)
            if match:
                question = match.group(1).strip()
                topics.append((question, paragraph, category_for_question(question, category_ids)))

        if not topics:
            continue

        first_question, first_content, first_category_id = topics[0]
        article.title = first_question
        article.content = first_content
        article.category_id = first_category_id
        article.save(using=database, update_fields=['title', 'content', 'category'])

        for topic_number, (question, content, category_id) in enumerate(topics[1:], start=2):
            suffix = f'-topic-{topic_number}'
            slug = f'{guide_slug[:220 - len(suffix)]}{suffix}'
            while HelpArticle.objects.using(database).filter(slug=slug).exists():
                topic_number += 1
                suffix = f'-topic-{topic_number}'
                slug = f'{guide_slug[:220 - len(suffix)]}{suffix}'
            HelpArticle.objects.using(database).create(
                category_id=category_id,
                title=question,
                slug=slug,
                audience=article.audience,
                content=content,
                video_tutorial_url=article.video_tutorial_url,
                is_kid_friendly=article.is_kid_friendly,
            )


def restore_help_guides(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    HelpCategory = apps.get_model('api', 'HelpCategory')
    database = schema_editor.connection.alias

    for guide_slug, guide_data in GUIDES.items():
        article = HelpArticle.objects.using(database).filter(slug=guide_slug).first()
        if not article:
            continue
        related_topics = list(
            HelpArticle.objects.using(database)
            .filter(slug__startswith=f'{guide_slug}-topic-')
        )
        related_topics.sort(
            key=lambda topic: int(re.search(r'-topic-(\d+)$', topic.slug).group(1)),
        )
        article.content = '\n\n'.join([article.content, *(topic.content for topic in related_topics)])
        article.title = guide_data['title']
        article.category = HelpCategory.objects.using(database).get(slug=guide_data['category'])
        article.save(using=database, update_fields=['content', 'title', 'category'])
        HelpArticle.objects.using(database).filter(pk__in=[topic.pk for topic in related_topics]).delete()

    HelpCategory.objects.using(database).filter(
        slug__in=[category['slug'] for category in CATEGORIES],
        articles__isnull=True,
    ).delete()
    email_category = HelpCategory.objects.using(database).filter(slug='email-delivery').first()
    if email_category:
        email_category.order = 3
        email_category.save(using=database, update_fields=['order'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0034_merge_learner_help_into_parent'),
    ]

    operations = [
        migrations.RunPython(categorize_help_topics, restore_help_guides),
    ]