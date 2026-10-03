from django.db import migrations


OLD_TEXT = 'Contact the Sgila team'
NEW_TEXT = 'Contact the SGILA team'


def capitalize_sgila(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias
    article = HelpArticle.objects.using(database).filter(
        slug='parent-contact-support',
    ).first()
    if article and OLD_TEXT in article.content:
        article.content = article.content.replace(OLD_TEXT, NEW_TEXT)
        article.save(using=database, update_fields=['content'])


def restore_sgila_casing(apps, schema_editor):
    HelpArticle = apps.get_model('api', 'HelpArticle')
    database = schema_editor.connection.alias
    article = HelpArticle.objects.using(database).filter(
        slug='parent-contact-support',
    ).first()
    if article and NEW_TEXT in article.content:
        article.content = article.content.replace(NEW_TEXT, OLD_TEXT)
        article.save(using=database, update_fields=['content'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0038_expand_enterprise_funding_options'),
    ]

    operations = [
        migrations.RunPython(capitalize_sgila, restore_sgila_casing),
    ]