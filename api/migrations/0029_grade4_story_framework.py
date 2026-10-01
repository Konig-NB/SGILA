from django.db import migrations, models


BLUEPRINTS = [
    ('The Shared Discovery', 'adventure', 'a school library and nearby park', 'a curious learner', 'The learner finds an unfamiliar object and must discover who needs it.', 'Clues and a conversation help the learner return it and bring neighbours together.', 'inference and responsible choices', ['school', 'community', 'kindness']),
    ('The Helpful Invention', 'problem-solving story', 'a South African primary school', 'a learner who likes making things', 'A familiar school problem makes a class activity difficult.', 'The learner tests a simple idea with classmates and improves it together.', 'sequencing and cause and effect', ['school', 'invention', 'teamwork']),
    ('A Community Garden', 'realistic fiction', 'a community garden near home', 'a young helper', 'A dry patch of ground is not producing enough food for a planned event.', 'Neighbours share knowledge and effort to care for the garden.', 'vocabulary and cooperation', ['community', 'nature', 'teamwork']),
    ('The Missing Message', 'mystery', 'a family home and local community hall', 'a careful young observer', 'An important invitation seems to have gone missing before a gathering.', 'The learner follows fair clues and asks people politely to solve the mix-up.', 'prediction and drawing conclusions', ['family', 'community', 'communication']),
    ('The Rainy Day Plan', 'adventure', 'a school during a rainy day', 'a thoughtful class member', 'Rain changes the plan for a class activity.', 'The class adapts its plan and includes everyone indoors.', 'sequencing and problem-solving', ['school', 'weather', 'teamwork']),
    ('The Kindness Challenge', 'realistic fiction', 'a neighbourhood sports field', 'a learner joining a group activity', 'A new participant feels left out of a team activity.', 'The main character listens, changes the rules fairly and makes space for others.', 'character feelings and empathy', ['community', 'sport', 'kindness']),
    ('The Market Morning', 'personal recount', 'a local South African market', 'a learner helping a family member', 'A small mix-up makes it hard to find the right stall and supplies.', 'Clear directions and careful checking solve the problem.', 'directions and details', ['family', 'market', 'communication']),
    ('The Nature Club', 'realistic fiction', 'a school nature club and local stream', 'a learner who notices small details', 'The club notices litter near a shared outdoor space.', 'Learners organise a safe clean-up with adult guidance and explain what they learned.', 'cause and effect and care for nature', ['school', 'nature', 'teamwork']),
]

VOCABULARY = [
    ('noticed', 'saw or became aware of something', 'verb', 'Lebo noticed a small sign beside the gate.', 1, ['school', 'community', 'observation']),
    ('carefully', 'in a way that avoids mistakes or harm', 'adverb', 'She carefully carried the box.', 1, ['school', 'safety']),
    ('decided', 'made a choice after thinking', 'verb', 'The group decided to work together.', 1, ['school', 'teamwork']),
    ('invited', 'asked someone to come or take part', 'verb', 'They invited their neighbour to join.', 1, ['community', 'communication']),
    ('discovered', 'found something or learned something new', 'verb', 'We discovered a path behind the garden.', 1, ['adventure', 'nature']),
    ('replied', 'answered someone', 'verb', 'The shopkeeper replied with a smile.', 1, ['market', 'communication']),
    ('worried', 'felt troubled about something', 'adjective', 'Musa felt worried about the missing note.', 1, ['feelings', 'family']),
    ('proud', 'pleased about something done well', 'adjective', 'The team felt proud of their work.', 1, ['feelings', 'teamwork']),
    ('patient', 'able to wait calmly', 'adjective', 'A patient helper listened to every idea.', 1, ['feelings', 'teamwork']),
    ('solution', 'an answer to a problem', 'noun', 'Their solution kept the books dry.', 1, ['problem-solving', 'school']),
    ('promise', 'words that show you will do something', 'noun', 'She kept her promise to return the key.', 1, ['family', 'community']),
    ('neighbour', 'a person who lives nearby', 'noun', 'Their neighbour watered the plants.', 1, ['community', 'kindness']),
    ('exchange', 'to give something and receive something else', 'verb', 'The learners exchanged ideas.', 2, ['communication', 'market']),
    ('prepare', 'to get ready for something', 'verb', 'They prepare the hall before the event.', 2, ['school', 'community']),
    ('compare', 'to look at how things are alike or different', 'verb', 'We compare the two maps.', 2, ['school', 'learning']),
    ('explain', 'to make an idea clear with details', 'verb', 'Anele can explain the new plan.', 2, ['communication', 'learning']),
    ('journey', 'a trip from one place to another', 'noun', 'Their journey to the library was short.', 2, ['adventure', 'travel']),
    ('community', 'people who live or work in the same area', 'noun', 'The community shared the garden.', 2, ['community', 'teamwork']),
    ('careful', 'taking care to avoid mistakes or harm', 'adjective', 'A careful reader checked the clue.', 2, ['school', 'safety']),
    ('gathered', 'came together in one place', 'verb', 'Families gathered under the tree.', 2, ['community', 'family']),
    ('message', 'information sent to another person', 'noun', 'The message gave the meeting time.', 2, ['communication', 'family']),
    ('suggested', 'offered an idea for others to consider', 'verb', 'Thandi suggested a different route.', 2, ['problem-solving', 'teamwork']),
    ('reached', 'arrived at or got to a place', 'verb', 'The class reached the hall before the rain.', 2, ['travel', 'school']),
    ('shared', 'used or enjoyed by more than one person', 'verb', 'The children shared their paints.', 2, ['teamwork', 'kindness']),
    ('improved', 'became better', 'verb', 'Their second plan improved the activity.', 2, ['problem-solving', 'learning']),
    ('recognised', 'knew or identified someone or something', 'verb', 'She recognised the red bag by the door.', 2, ['observation', 'nature']),
    ('invitation', 'a request to come to an event', 'noun', 'The invitation included a clear address.', 2, ['communication', 'community']),
    ('decision', 'a choice made after thinking', 'noun', 'Their decision helped the whole team.', 2, ['problem-solving', 'teamwork']),
    ('ordinary', 'usual or not special', 'adjective', 'An ordinary box became a bird feeder.', 2, ['invention', 'school']),
    ('surprised', 'feeling something unexpected has happened', 'adjective', 'The children were surprised by the result.', 2, ['feelings', 'adventure']),
    ('delighted', 'very pleased', 'adjective', 'Auntie was delighted with the garden.', 3, ['feelings', 'nature']),
    ('determined', 'not giving up on a goal', 'adjective', 'The determined group tried once more.', 3, ['feelings', 'teamwork']),
    ('encouraged', 'gave someone confidence or support', 'verb', 'The coach encouraged every learner.', 3, ['sport', 'kindness']),
    ('responsible', 'trusted to do what is right', 'adjective', 'A responsible helper returned the tools.', 3, ['community', 'safety']),
    ('disappointed', 'sad because something did not happen as hoped', 'adjective', 'He felt disappointed when the match was moved.', 3, ['feelings', 'sport']),
    ('repaired', 'fixed something that was broken', 'verb', 'They repaired the loose sign together.', 3, ['problem-solving', 'community']),
    ('confident', 'sure about your ability to do something', 'adjective', 'She felt confident after practising.', 3, ['feelings', 'learning']),
    ('grateful', 'feeling thankful', 'adjective', 'We were grateful for the extra help.', 3, ['feelings', 'kindness']),
    ('whispered', 'spoke very quietly', 'verb', 'Sipho whispered the clue to his friend.', 3, ['communication', 'mystery']),
    ('searched', 'looked carefully for something', 'verb', 'They searched the classroom for the map.', 3, ['mystery', 'school']),
    ('surroundings', 'the places and things around someone', 'noun', 'They kept their surroundings tidy.', 3, ['nature', 'community']),
    ('reusable', 'able to be used again', 'adjective', 'The club collected reusable containers.', 3, ['nature', 'community']),
    ('valuable', 'useful or important', 'adjective', 'Every idea was valuable to the group.', 3, ['teamwork', 'learning']),
    ('disagreement', 'a difference of opinion', 'noun', 'The friends solved their disagreement calmly.', 3, ['communication', 'teamwork']),
    ('instructions', 'directions that explain what to do', 'noun', 'The instructions showed each step.', 3, ['learning', 'communication']),
    ('celebrated', 'showed happiness about an achievement', 'verb', 'They celebrated their successful project.', 3, ['community', 'teamwork']),
    ('organised', 'arranged things in a planned way', 'verb', 'The class organised the books by topic.', 3, ['school', 'teamwork']),
]


def seed_framework(apps, schema_editor):
    Blueprint = apps.get_model('api', 'Grade4StoryBlueprint')
    Vocabulary = apps.get_model('api', 'Grade4VocabularyItem')
    for name, genre, setting, role, challenge, resolution, focus, tags in BLUEPRINTS:
        Blueprint.objects.using(schema_editor.connection.alias).update_or_create(
            name=name,
            defaults={'genre': genre, 'setting': setting, 'character_role': role,
                      'challenge': challenge, 'resolution_pattern': resolution,
                      'learning_focus': focus, 'vocabulary_tags': tags, 'active': True},
        )
    for word, meaning, part, example, term, tags in VOCABULARY:
        Vocabulary.objects.using(schema_editor.connection.alias).update_or_create(
            word=word,
            defaults={'meaning': meaning, 'part_of_speech': part, 'example': example,
                      'term': term, 'tags': tags, 'active': True},
        )


class Migration(migrations.Migration):
    dependencies = [('api', '0028_merge_20260927_2257')]
    operations = [
        migrations.CreateModel(
            name='Grade4StoryBlueprint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('genre', models.CharField(max_length=40)),
                ('setting', models.CharField(max_length=160)),
                ('character_role', models.CharField(max_length=120)),
                ('challenge', models.TextField()),
                ('resolution_pattern', models.TextField()),
                ('learning_focus', models.CharField(max_length=120)),
                ('vocabulary_tags', models.JSONField(blank=True, default=list)),
                ('active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Grade4VocabularyItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(max_length=80, unique=True)),
                ('meaning', models.CharField(max_length=240)),
                ('part_of_speech', models.CharField(blank=True, max_length=40)),
                ('example', models.CharField(blank=True, max_length=240)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('term', models.PositiveSmallIntegerField(default=1)),
                ('active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['word']},
        ),
        migrations.AddField(
            model_name='lesson',
            name='generation_metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(seed_framework, migrations.RunPython.noop),
    ]
