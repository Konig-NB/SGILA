from django.db import migrations


CATEGORY = {
    'name': 'Support and feedback',
    'slug': 'support-feedback',
    'description': 'Contact the SGILA team for help or share feedback',
    'order': 9,
}

TOPICS = (
    {
        'title': 'Can I add more than one child to my Parent account?',
        'slug': 'parent-add-multiple-children',
        'category': 'getting-started-guides',
        'content': (
            'Q: Can I add more than one child to my Parent account? A: Yes. Choose '
            'Add child on your Parent dashboard to create a separate learner profile '
            'for each child. The number of active learners depends on your plan. If '
            'you reach its limit, review your plan options or add a seat if your plan '
            'allows it.'
        ),
    },
    {
        'title': "How do I update my child's grade for a new school year?",
        'slug': 'parent-update-child-grade',
        'category': 'getting-started-guides',
        'content': (
            "Q: How do I update my child's grade for a new school year? A: When grade "
            'confirmation appears on your Parent dashboard, choose the suggested '
            'grade, keep the current grade if your child is repeating, or select a '
            'different grade. SGILA does not promote learners automatically.'
        ),
    },
    {
        'title': 'How can I contact SGILA support?',
        'slug': 'parent-contact-support',
        'category': 'support-feedback',
        'content': (
            'Q: How can I contact SGILA support? A: Open Contact the Sgila team at '
            'the bottom of this page and send a message with your email, a subject, '
            'and the details of your question. You can also email '
            'sgila.info@gmail.com.'
        ),
    },
)


def add_parent_topics(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    HelpCategory = apps.get_model('api', 'HelpCategory')
    database = schema_editor.connection.alias

    support_category, _created = HelpCategory.objects.using(database).get_or_create(
        slug=CATEGORY['slug'],
        defaults=CATEGORY,
    )
    category_ids = {'support-feedback': support_category.pk}
    for slug in ('getting-started-guides',):
        category_ids[slug] = HelpCategory.objects.using(database).get(slug=slug).pk

    for topic in TOPICS:
        HelpArticle.objects.using(database).get_or_create(
            slug=topic['slug'],
            defaults={
                'title': topic['title'],
                'category_id': category_ids[topic['category']],
                'audience': 'parent',
                'content': topic['content'],
                'is_kid_friendly': False,
            },
        )


def remove_parent_topics(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    HelpCategory = apps.get_model('api', 'HelpCategory')
    database = schema_editor.connection.alias

    HelpArticle.objects.using(database).filter(
        slug__in=[topic['slug'] for topic in TOPICS],
    ).delete()
    HelpCategory.objects.using(database).filter(
        slug=CATEGORY['slug'],
        articles__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0035_categorize_help_topics'),
    ]

    operations = [
        migrations.RunPython(add_parent_topics, remove_parent_topics),
    ]