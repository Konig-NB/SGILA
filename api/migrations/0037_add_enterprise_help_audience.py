from django.db import migrations, models


CATEGORY = {
    'name': 'Enterprise packages',
    'slug': 'enterprise-packages',
    'description': 'School, district, and government-funded SGILA packages',
    'order': 10,
}

TOPICS = (
    (
        'What is an Enterprise package?',
        'enterprise-package-overview',
        'Q: What is an Enterprise package? A: It brings SGILA to a school, district, '
        'or province through a government-funded education budget. Enterprise '
        'packages do not use per-family payments or require a payment card.',
    ),
    (
        'Who can use an Enterprise package?',
        'enterprise-package-eligibility',
        'Q: Who can use an Enterprise package? A: Enterprise packages are for '
        'schools, groups of schools in a district, and provincial or national '
        'education departments arranging a government-funded rollout.',
    ),
    (
        'What does a School package include?',
        'enterprise-school-package-includes',
        'Q: What does a School package include? A: It covers learner and teacher '
        'accounts for one school, class and grade progress dashboards, and one '
        'package code for that school. The School package has no learner limit.',
    ),
    (
        'What does a District package include?',
        'enterprise-district-package-includes',
        'Q: What does a District package include? A: It includes the School package '
        'for every school in the district, bulk onboarding support for rural or '
        'low-connectivity schools, and one code shared across the district schools.',
    ),
    (
        'What does a Province or National package include?',
        'enterprise-province-package-includes',
        'Q: What does a Province or National package include? A: It extends the '
        'District package to a provincial or national rollout, with dedicated '
        'onboarding and reporting for the department. Multiple codes can be issued '
        'as schools are added.',
    ),
    (
        'How does a school activate its Enterprise package?',
        'enterprise-activate-school-package',
        'Q: How does a school activate its Enterprise package? A: Open the plan page, '
        'enter the school name and the package code provided by your district or '
        'government contact, then choose Activate school package. No payment card '
        'is required.',
    ),
    (
        'Where can I get an Enterprise package code?',
        'enterprise-get-package-code',
        'Q: Where can I get an Enterprise package code? A: Get the code from the '
        'district or government contact arranging your school package. If you need '
        'help choosing a package, contact SGILA support at sgila.support@gmail.com.',
    ),
    (
        'My Enterprise package code is not working. What should I do?',
        'enterprise-package-code-help',
        'Q: My Enterprise package code is not working. What should I do? A: Check '
        'that you entered the school name and the code supplied by your district or '
        'government contact. If activation still does not work, contact that provider '
        'or email sgila.support@gmail.com for help.',
    ),
    (
        'Does an Enterprise package require a card or per-family payment?',
        'enterprise-package-payment',
        'Q: Does an Enterprise package require a card or per-family payment? A: No. '
        'Enterprise packages are funded through a government education budget and '
        'activated with a package code. There is no card payment or per-family cost.',
    ),
)


def add_enterprise_topics(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    HelpCategory = apps.get_model('api', 'HelpCategory')
    database = schema_editor.connection.alias

    category, _created = HelpCategory.objects.using(database).get_or_create(
        slug=CATEGORY['slug'],
        defaults=CATEGORY,
    )
    for title, slug, content in TOPICS:
        HelpArticle.objects.using(database).get_or_create(
            slug=slug,
            defaults={
                'category_id': category.pk,
                'title': title,
                'audience': 'enterprise',
                'content': content,
                'is_kid_friendly': False,
            },
        )


def remove_enterprise_topics(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    HelpCategory = apps.get_model('api', 'HelpCategory')
    database = schema_editor.connection.alias

    HelpArticle.objects.using(database).filter(
        slug__in=[slug for _title, slug, _content in TOPICS],
    ).delete()
    HelpCategory.objects.using(database).filter(
        slug=CATEGORY['slug'],
        articles__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0036_add_parent_help_topics'),
    ]

    operations = [
        migrations.AlterField(
            model_name='helparticle',
            name='audience',
            field=models.CharField(
                choices=[
                    ('teacher', 'Teacher'),
                    ('parent', 'Parent'),
                    ('learner', 'Learner'),
                    ('general', 'General'),
                    ('enterprise', 'Enterprise'),
                ],
                default='general',
                max_length=10,
            ),
        ),
        migrations.RunPython(add_enterprise_topics, remove_enterprise_topics),
    ]