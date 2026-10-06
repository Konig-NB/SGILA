from django.db import migrations


ARTICLES = (
    {
        'title': "I did not receive a verification or password-reset email",
        'slug': 'email-verification-or-password-reset',
        'audience': 'general',
        'is_kid_friendly': False,
        'content': (
            'Check that you entered the right email address, then look in Spam or Junk. '
            'In Gmail, also check Promotions and search for SGILA.\n\n'
            'Wait a few minutes before requesting another message. If you requested a '
            'verification code more than once, use the newest email; older codes may '
            'have expired.\n\n'
            'If no message arrives, email delivery may be unavailable or the sending '
            'service may have rejected the request. Contact your school or site '
            'administrator and include the time you made the request. Never share your '
            'password or verification code.'
        ),
    },
    {
        'title': 'Set up email delivery for a local SGILA installation',
        'slug': 'configure-sgila-email-delivery',
        'audience': 'general',
        'is_kid_friendly': False,
        'content': (
            'Copy .env.example to .env in the project folder. Set EMAIL_HOST_USER to '
            'the sending email address and EMAIL_HOST_PASSWORD to its SMTP or app '
            'password. For Gmail, use a Google App Password rather than the regular '
            'account password. Keep .env private and do not commit it.\n\n'
            'The example uses smtp.gmail.com on port 587 with TLS. Restart the Django '
            'server after changing .env. When valid SMTP credentials are not loaded, '
            'SGILA uses a console backend and prints outgoing messages in the server '
            'terminal instead of delivering them. Check that terminal for SMTP login '
            'or connection errors.'
        ),
    },
    {
        'title': 'My support request was submitted but no confirmation arrived',
        'slug': 'support-request-email-confirmation',
        'audience': 'general',
        'is_kid_friendly': False,
        'content': (
            'A support request can be saved even when email delivery is unavailable. '
            'Check Spam or Junk for a confirmation first. If the form said the request '
            'was saved but email delivery was not configured, the support team did not '
            'receive an email notification.\n\n'
            'For help with your request, email sgila.info@gmail.com directly. If '
            'you administer this SGILA installation, configure SMTP as described in '
            'the email delivery setup guide and check the server logs for sending '
            'errors.'
        ),
    },
)


def seed_email_guides(apps, schema_editor):
    HelpCategory = apps.get_model('api', 'HelpCategory')
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias

    category, _created = HelpCategory.objects.using(database).get_or_create(
        slug='email-delivery',
        defaults={
            'name': 'Email delivery',
            'description': 'Verification, password resets, and support messages',
            'icon_name': 'mail',
            'order': 3,
        },
    )
    for article in ARTICLES:
        HelpArticle.objects.using(database).get_or_create(
            slug=article['slug'],
            defaults={**article, 'category_id': category.pk},
        )


def remove_email_guides(apps, schema_editor):
    HelpCategory = apps.get_model('api', 'HelpCategory')
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias

    HelpArticle.objects.using(database).filter(
        slug__in=[article['slug'] for article in ARTICLES],
    ).delete()
    HelpCategory.objects.using(database).filter(
        slug='email-delivery',
        articles__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0029_helpcategory_supportticket_helparticle'),
    ]

    operations = [
        migrations.RunPython(seed_email_guides, remove_email_guides),
    ]