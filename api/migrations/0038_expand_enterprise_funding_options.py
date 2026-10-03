from django.db import migrations


OLD_CATEGORY_DESCRIPTION = 'School, district, and government-funded SGILA packages'
NEW_CATEGORY_DESCRIPTION = 'School, sponsor, district, and government-funded SGILA packages'

OLD_CONTENT = {
    'enterprise-package-overview': (
        'Q: What is an Enterprise package? A: It brings SGILA to a school, district, '
        'or province through a government-funded education budget. Enterprise '
        'packages do not use per-family payments or require a payment card.'
    ),
    'enterprise-package-eligibility': (
        'Q: Who can use an Enterprise package? A: Enterprise packages are for '
        'schools, groups of schools in a district, and provincial or national '
        'education departments arranging a government-funded rollout.'
    ),
    'enterprise-activate-school-package': (
        'Q: How does a school activate its Enterprise package? A: Open the plan page, '
        'enter the school name and the package code provided by your district or '
        'government contact, then choose Activate school package. No payment card '
        'is required.'
    ),
    'enterprise-get-package-code': (
        'Q: Where can I get an Enterprise package code? A: Get the code from the '
        'district or government contact arranging your school package. If you need '
        'help choosing a package, contact SGILA support at sgila.info@gmail.com.'
    ),
    'enterprise-package-code-help': (
        'Q: My Enterprise package code is not working. What should I do? A: Check '
        'that you entered the school name and the code supplied by your district or '
        'government contact. If activation still does not work, contact that provider '
        'or email sgila.info@gmail.com for help.'
    ),
    'enterprise-package-payment': (
        'Q: Does an Enterprise package require a card or per-family payment? A: No. '
        'Enterprise packages are funded through a government education budget and '
        'activated with a package code. There is no card payment or per-family cost.'
    ),
}

NEW_CONTENT = {
    'enterprise-package-overview': (
        'Q: What is an Enterprise package? A: It brings SGILA to a school, district, '
        'or province. Funding can come from the school itself, a sponsor, a district, '
        'or a government education budget. Enterprise packages use package codes, '
        'not per-family payments, and activation does not require a payment card.'
    ),
    'enterprise-package-eligibility': (
        'Q: Who can use an Enterprise package? A: Enterprise packages support a '
        'single school, groups of schools in a district, or provincial and national '
        'education rollouts. A public or private school, district, government '
        'department, or sponsor can arrange funding for a package.'
    ),
    'enterprise-activate-school-package': (
        'Q: How does a school activate its Enterprise package? A: Open the plan page, '
        'enter the school name and the package code provided by the organization '
        'arranging the package, then choose Activate school package. No payment card '
        'is required.'
    ),
    'enterprise-get-package-code': (
        'Q: Where can I get an Enterprise package code? A: Get the code from the '
        'organization arranging your package, such as your school, sponsor, district, '
        'or government contact. If your school is self-funding and needs a package '
        'code, contact SGILA support at sgila.info@gmail.com.'
    ),
    'enterprise-package-code-help': (
        'Q: My Enterprise package code is not working. What should I do? A: Check '
        'that you entered the school name and the code supplied by your package '
        'provider or sponsor. If activation still does not work, contact that '
        'provider or email sgila.info@gmail.com for help.'
    ),
    'enterprise-package-payment': (
        'Q: Does an Enterprise package require a card or per-family payment? A: No. '
        'A school can fund its own package, or a sponsor, district, government '
        'department, or another organization can fund it. Activation uses a package '
        'code; families do not pay individually and no payment card is required.'
    ),
}

NEW_TOPIC = {
    'title': 'Can a sponsor or private school fund an Enterprise package?',
    'slug': 'enterprise-school-or-sponsor-funding',
    'content': (
        'Q: Can a sponsor or private school fund an Enterprise package? A: Yes. A '
        'private school can fund its own package, or an external sponsor can fund it. '
        'Districts and government departments can also arrange funding. Ask the '
        'organization funding the package for its code, or contact '
        'sgila.info@gmail.com for help.'
    ),
}


def broaden_enterprise_funding(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    HelpCategory = apps.get_model('api', 'HelpCategory')
    database = schema_editor.connection.alias

    HelpCategory.objects.using(database).filter(slug='enterprise-packages').update(
        description=NEW_CATEGORY_DESCRIPTION,
    )
    for slug, content in NEW_CONTENT.items():
        HelpArticle.objects.using(database).filter(slug=slug).update(content=content)

    category = HelpCategory.objects.using(database).get(slug='enterprise-packages')
    HelpArticle.objects.using(database).get_or_create(
        slug=NEW_TOPIC['slug'],
        defaults={
            'category_id': category.pk,
            'title': NEW_TOPIC['title'],
            'audience': 'enterprise',
            'content': NEW_TOPIC['content'],
            'is_kid_friendly': False,
        },
    )


def restore_enterprise_funding(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    HelpCategory = apps.get_model('api', 'HelpCategory')
    database = schema_editor.connection.alias

    HelpArticle.objects.using(database).filter(slug=NEW_TOPIC['slug']).delete()
    for slug, content in OLD_CONTENT.items():
        HelpArticle.objects.using(database).filter(slug=slug).update(content=content)
    HelpCategory.objects.using(database).filter(slug='enterprise-packages').update(
        description=OLD_CATEGORY_DESCRIPTION,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0037_add_enterprise_help_audience'),
    ]

    operations = [
        migrations.RunPython(broaden_enterprise_funding, restore_enterprise_funding),
    ]