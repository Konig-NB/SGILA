from django.conf import settings

from api.grade4_story_framework import grade4_assessed_item_count
from api.models import AIStoryJob, Lesson, Progress


AI_STORY_PASS_THRESHOLD = 95


def lesson_passed(child, lesson):
    """Check lesson completion, applying the score threshold only when enabled."""
    record = Progress.objects.filter(child=child, lesson=lesson).first()
    if not record:
        return False
    if getattr(settings, 'ENABLE_STORY_THRESHOLDS', False):
        if record.percentage < AI_STORY_PASS_THRESHOLD:
            return False
        if lesson.grade == 4 and lesson.is_ai_generated and lesson.reading_activities.exists():
            return record.total_possible >= grade4_assessed_item_count(lesson)
    return True


def check_ai_story_eligibility(child, grade):
    """Return whether a learner may start another story for this grade."""
    if grade not in (1, 2, 3, 4):
        return False, 'AI practice stories are available for Grades 1 to 4.', f'/grade/{grade}'
    if not getattr(settings, 'ENABLE_STORY_THRESHOLDS', False):
        return True, None, None

    all_lessons = Lesson.objects.filter(grade=grade)
    required_lessons = list(all_lessons.filter(is_ai_generated=False)) + list(all_lessons.filter(
        is_ai_generated=True,
        generated_for__isnull=True,
        curriculum_source='AI story collection — CAPS aligned',
    ))
    if not required_lessons or not all(lesson_passed(child, lesson) for lesson in required_lessons):
        requirement = (
            f'Score at least {AI_STORY_PASS_THRESHOLD}% on every workbook story before creating an AI story.'
            if getattr(settings, 'ENABLE_STORY_THRESHOLDS', False)
            else 'Complete every workbook story before creating an AI story.'
        )
        return (
            False,
            requirement,
            f'/grade/{grade}',
        )

    current_ai_lesson = Lesson.objects.filter(
        grade=grade,
        is_ai_generated=True,
        generated_for=child,
    ).order_by('-created_at').first()
    if current_ai_lesson and not lesson_passed(child, current_ai_lesson):
        requirement = (
            f'Finish your current story with at least {AI_STORY_PASS_THRESHOLD}% before unlocking a new one.'
            if getattr(settings, 'ENABLE_STORY_THRESHOLDS', False)
            else 'Finish your current story before unlocking a new one.'
        )
        return (
            False,
            requirement,
            f'/lessons/{current_ai_lesson.id}/story',
        )

    return True, None, None