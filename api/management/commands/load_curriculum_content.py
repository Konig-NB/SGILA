import copy

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import (
    CauseEffectPair,
    ComprehensionQuestion,
    FeelingsQuestion,
    InferenceQuestion,
    Lesson,
    PredictionQuestion,
    PronunciationWord,
    ReadingActivity,
    SequencingActivity,
    SpellingActivity,
    StoryPage,
    ThemeQuestion,
    VisualActivityItem,
    VocabularyQuestion,
    WrittenResponsePrompt,
)
from api.management.commands.seed_data import Command as SeedDataCommand


CONTENT_MODELS = (
    StoryPage,
    ComprehensionQuestion,
    ReadingActivity,
    VisualActivityItem,
    PronunciationWord,
    SpellingActivity,
    VocabularyQuestion,
    SequencingActivity,
    InferenceQuestion,
    PredictionQuestion,
    FeelingsQuestion,
    CauseEffectPair,
    ThemeQuestion,
    WrittenResponsePrompt,
)

LESSON_ALIASES = {
    "Lerato's Fruit Basket": ["Lerato's Fruit Basket"],
    'A Very Hot Day': ['A Very Hot Day'],
    "A Dog's Life": ["A Dog's Life", 'Lebo and the Lion'],
    'A New Baby': ['A New Baby', 'The Big River'],
    "Mandu's Secret Diary": ["Mandu's Secret Diary", 'Grandma Finds a Map'],
    "Mandu's Running Shoes": ["Mandu's Running Shoes", 'The Day the Water Stopped'],
    'Why Mapula Missed School': ['Why Mapula Missed School', 'The Skateboard Shortcut'],
    'Best Friends to the Rescue': ['Best Friends to the Rescue', 'The Jersey That Did Not Fit'],
    'The Terrible Twins': ['The Terrible Twins', 'Eyes in the Cupboard'],
    "Frog and Crow's Wrong Message": ["Frog and Crow's Wrong Message", 'The Crushed Birthday Flowers'],
}


class Command(BaseCommand):
    help = 'Load the Grade 1-4 curriculum content without deleting user accounts or progress.'

    def clone_content(self, source, target):
        for model in CONTENT_MODELS:
            model.objects.filter(lesson=target).delete()
            for source_object in model.objects.filter(lesson=source):
                values = {}
                for field in source_object._meta.concrete_fields:
                    if field.primary_key or field.name == 'lesson':
                        continue
                    values[field.name] = copy.deepcopy(getattr(source_object, field.name))
                model.objects.create(lesson=target, **values)

        target.title = source.title
        target.grade = source.grade
        target.thumbnail_image = source.thumbnail_image
        target.save(update_fields=['title', 'grade', 'thumbnail_image'])

    @transaction.atomic
    def handle(self, *args, **kwargs):
        seed = SeedDataCommand()
        generated = [seed.create_lerato_lesson()]
        existing_ids = set(Lesson.objects.values_list('id', flat=True))
        seed.create_big_book_lessons()
        generated.extend(Lesson.objects.exclude(id__in=existing_ids).order_by('id'))

        for source in generated:
            aliases = LESSON_ALIASES.get(source.title, [source.title])
            target = (
                Lesson.objects.filter(grade=source.grade, title__in=aliases)
                .exclude(id=source.id)
                .order_by('id')
                .first()
            )
            if not target:
                continue
            self.clone_content(source, target)
            source.delete()

        self.stdout.write(self.style.SUCCESS(
            'Grade 1-4 curriculum content loaded. Existing accounts and progress were preserved.'
        ))
