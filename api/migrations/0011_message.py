from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_grade4activityprogress'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender_role', models.CharField(choices=[('parent', 'Parent'), ('teacher', 'Teacher')], max_length=10)),
                ('body', models.TextField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
                ('child', models.ForeignKey(
                    help_text='The learner this conversation is about.',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages',
                    to='api.child',
                )),
                ('sender_parent', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sent_messages',
                    to='api.parent',
                )),
                ('sender_teacher', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sent_messages',
                    to='api.teacher',
                )),
            ],
            options={
                'ordering': ['sent_at'],
            },
        ),
    ]
