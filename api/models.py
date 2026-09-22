import random
import string
from datetime import date, timedelta

from django.db import models
from django.utils import timezone


def capitalize_first(value):
    """Return text with its first non-space character capitalized."""
    value = (value or '').strip()
    for index, character in enumerate(value):
        if character.isalpha():
            return f'{value[:index]}{character.upper()}{value[index + 1:]}'
    return value


def title_case(value):
    """Return trimmed text with every word title-cased."""
    return (value or '').strip().title()


def generate_class_code():
    """Generate a short teacher/class code for parent and learner linking."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def current_school_year():
    """South African school years run Jan-Dec, so the academic/school year is just the calendar year."""
    return date.today().year


class Parent(models.Model):
    """Guardian account that can manage one or more learner profiles."""
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=300)
    phone = models.CharField(max_length=30, blank=True)
    accepted_popia = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    auth_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        self.full_name = title_case(self.full_name)
        super().save(*args, **kwargs)


class Teacher(models.Model):
    """Teacher account for monitoring class progress."""
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=300)
    school_name = models.CharField(max_length=160)
    grades_taught = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    accepted_popia = models.BooleanField(default=False)
    class_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    auth_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        self.full_name = title_case(self.full_name)
        self.school_name = title_case(self.school_name)
        super().save(*args, **kwargs)


class Child(models.Model):
    """Stores every registered child in the app."""
    parent = models.ForeignKey(Parent, on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='learners')
    teacher_class = models.ForeignKey('TeacherClass', on_delete=models.SET_NULL, null=True, blank=True, related_name='learners')
    username = models.CharField(max_length=40, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    # Kept as a stored column (rather than computed only on read) so it can be used
    # directly in querysets/reports. It is always recalculated from date_of_birth
    # in save() below, and opportunistically refreshed by refresh_age_if_stale()
    # whenever the child is loaded in a view — so it keeps itself correct every
    # birthday/new year without needing a scheduled task.
    age = models.IntegerField(null=True, blank=True)
    grade = models.IntegerField()          # 1 to 4 — the grade the child is currently shown content for.
    # The school year (calendar year) for which `grade` was last confirmed by a parent or
    # teacher. This is what makes grade changes an explicit human decision rather than
    # something the app infers from app usage — see needs_grade_confirmation() below and
    # GradeHistory for the full record of what was confirmed each year.
    grade_confirmed_year = models.IntegerField(null=True, blank=True)
    # The school year we last emailed the parent a "please confirm the grade"
    # reminder for. Separate from grade_confirmed_year so the reminder job can
    # tell "already reminded, don't spam" apart from "already confirmed, don't remind".
    grade_reminder_sent_year = models.IntegerField(null=True, blank=True)
    school_name = models.CharField(max_length=160, blank=True)
    deactivated_reason = models.CharField(max_length=120, blank=True, default='')
    parent_email = models.EmailField()
    photo = models.FileField(upload_to='child_photos/', blank=True)
    password = models.CharField(max_length=300)   # hashed by Django
    paused_activities = models.JSONField(default=dict, blank=True)

    # --- Deactivation ------------------------------------------------------
    # A learner can be paused two ways: individually (a parent turns off just
    # this one child from the learner report) or as part of the parent's own
    # account being deactivated (every currently-active child is swept along
    # with it). `deactivated_reason` is what lets reactivation tell those
    # apart: reactivating the parent only brings back children whose reason
    # is DEACTIVATED_PARENT_CASCADE. A child the parent paused on purpose
    # (DEACTIVATED_MANUAL) stays off until reactivated on its own, even after
    # the parent account comes back.
    DEACTIVATED_PARENT_CASCADE = 'parent_cascade'
    DEACTIVATED_MANUAL = 'manual'
    DEACTIVATED_REASON_CHOICES = [
        (DEACTIVATED_PARENT_CASCADE, "Parent account deactivated"),
        (DEACTIVATED_MANUAL, "Deactivated individually"),
    ]
    is_active = models.BooleanField(default=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivated_reason = models.CharField(max_length=20, choices=DEACTIVATED_REASON_CHOICES, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Grade {self.grade})"

    def calculate_age(self):
        """Return the child's current age worked out from date_of_birth as of today.

        Falls back to the existing stored age if no date_of_birth is on file yet
        (e.g. profiles created before this field existed).
        """
        if not self.date_of_birth:
            return self.age
        today = date.today()
        years = today.year - self.date_of_birth.year
        had_birthday_this_year = (today.month, today.day) >= (self.date_of_birth.month, self.date_of_birth.day)
        if not had_birthday_this_year:
            years -= 1
        return years

    def refresh_age_if_stale(self):
        """Recalculate age from date_of_birth and persist it if it has drifted.

        Call this whenever a child record is loaded in a view. It only writes to
        the database when the stored age is actually out of date (e.g. a birthday
        has passed since the last save), so it is cheap to call on every request.
        """
        if not self.date_of_birth:
            return
        current_age = self.calculate_age()
        if current_age != self.age:
            self.age = current_age
            self.save(update_fields=['age'])

    def save(self, *args, **kwargs):
        self.username = capitalize_first(self.username) or None
        self.first_name = title_case(self.first_name)
        self.last_name = title_case(self.last_name)
        self.name = title_case(self.name)
        self.school_name = title_case(self.school_name)
        self.deactivated_reason = (self.deactivated_reason or '').strip()
        if self.date_of_birth:
            self.age = self.calculate_age()
        super().save(*args, **kwargs)

    def needs_grade_confirmation(self):
        """True once a new school year has started and nobody has confirmed this
        child's real-world grade for it yet.

        The app never advances `grade` on its own — completing lessons proves
        content mastery, not that the school promoted the child. Instead, once a
        new school year begins, this flags the child so the parent/teacher
        dashboard can ask a human: 'What grade is <name> actually in now?'
        """
        return self.grade_confirmed_year is None or self.grade_confirmed_year < current_school_year()

    def reminder_already_sent_this_year(self):
        """True if send_grade_reminders already emailed this child's parent for
        the current school year — keeps the reminder to one email per year."""
        return self.grade_reminder_sent_year == current_school_year()

    def mark_reminder_sent(self):
        self.grade_reminder_sent_year = current_school_year()
        self.save(update_fields=['grade_reminder_sent_year'])

    def suggested_next_grade(self):
        """Default suggestion shown alongside the confirmation prompt — the parent
        or teacher can accept it, pick a different grade (e.g. repeated), or leave
        the child where they are. Never applied automatically."""
        return min(self.grade + 1, 4)

    def record_grade_confirmation(self, grade, confirmed_by, confirmed_by_name=''):
        """Apply a human-confirmed grade for the current school year and log it.

        `confirmed_by` should be one of GradeHistory.CONFIRMED_BY_CHOICES values.
        This is the ONLY place `grade` should change after registration — it is
        always the result of an explicit confirmation, never an automatic rollover.
        """
        year = current_school_year()
        previous_grade = self.grade
        self.grade = grade
        self.grade_confirmed_year = year
        self.save(update_fields=['grade', 'grade_confirmed_year'])
        GradeHistory.objects.update_or_create(
            child=self,
            year=year,
            defaults={
                'grade': grade,
                'repeated': confirmed_by != GradeHistory.REGISTRATION and grade == previous_grade,
                'confirmed_by': confirmed_by,
                'confirmed_by_name': confirmed_by_name,
            },
        )
        return self

    def deactivate(self, reason):
        """Pause this learner's access. `reason` is one of DEACTIVATED_REASON_CHOICES."""
        self.is_active = False
        self.deactivated_at = timezone.now()
        self.deactivated_reason = reason
        self.save(update_fields=['is_active', 'deactivated_at', 'deactivated_reason'])

    def reactivate(self):
        self.is_active = True
        self.deactivated_at = None
        self.deactivated_reason = ''
        self.save(update_fields=['is_active', 'deactivated_at', 'deactivated_reason'])


class GradeHistory(models.Model):
    """Records the human-confirmed grade for a child for one school year.

    One row per child per year — this is the audit trail behind
    Child.grade_confirmed_year, and lets a parent/teacher see a learner's real
    grade progression over time (including repeated years).
    """
    PARENT = 'parent'
    TEACHER = 'teacher'
    REGISTRATION = 'registration'
    CONFIRMED_BY_CHOICES = [
        (PARENT, 'Parent'),
        (TEACHER, 'Teacher'),
        (REGISTRATION, 'Set at registration'),
    ]

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='grade_history')
    year = models.IntegerField()
    grade = models.IntegerField()
    repeated = models.BooleanField(default=False)
    confirmed_by = models.CharField(max_length=20, choices=CONFIRMED_BY_CHOICES)
    confirmed_by_name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year']
        constraints = [
            models.UniqueConstraint(fields=['child', 'year'], name='unique_child_grade_year'),
        ]

    def __str__(self):
        return f"{self.child.name} — {self.year} — Grade {self.grade}"


class TeacherClass(models.Model):
    """Named class/group owned by a teacher and joined through a class code."""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='classes')
    name = models.CharField(max_length=80)
    grade = models.IntegerField(default=1)
    class_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    # Set true when the owning teacher is deactivated, so dashboards/admin can
    # surface "this class needs a new teacher" instead of silently going quiet.
    needs_new_teacher = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['grade', 'name']

    def __str__(self):
        return f"{self.teacher.full_name} - {self.name}"

    def save(self, *args, **kwargs):
        self.name = capitalize_first(self.name)
        super().save(*args, **kwargs)


class Lesson(models.Model):
    """One lesson card shown on the home page."""
    title = models.CharField(max_length=200)
    grade = models.IntegerField()
    thumbnail_image = models.CharField(max_length=300, blank=True)
    curriculum_source = models.CharField(max_length=120, blank=True)
    source_attribution = models.TextField(blank=True)
    is_ai_generated = models.BooleanField(default=False)
    # AI-generated stories belong to the learner who unlocked them. Workbook
    # lessons (and any shared/reviewed AI stories) have no owner and remain
    # available to every learner in the grade.
    generated_for = models.ForeignKey(
        Child, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='generated_lessons',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class StoryPage(models.Model):
    """One page inside a story — text + image + audio."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField()
    text = models.TextField()
    image_url = models.CharField(max_length=300, blank=True)
    audio_url = models.CharField(max_length=300, blank=True)
    # Stored as comma-separated values e.g. "apple,banana,orange"
    highlighted_words = models.TextField(blank=True)

    class Meta:
        ordering = ['page_number']

    def get_highlighted_words(self):
        """Return highlighted_words as a Python list."""
        if self.highlighted_words:
            return [w.strip() for w in self.highlighted_words.split(',')]
        return []

    def __str__(self):
        return f"{self.lesson.title} — Page {self.page_number}"


class ComprehensionQuestion(models.Model):
    """Multiple-choice question for a lesson."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    option_1 = models.CharField(max_length=200)
    option_2 = models.CharField(max_length=200)
    option_3 = models.CharField(max_length=200)
    option_4 = models.CharField(max_length=200)
    # correct_answer is NEVER sent to frontend before the child answers
    correct_answer = models.CharField(max_length=200)

    def get_options(self):
        return [self.option_1, self.option_2, self.option_3, self.option_4]

    def __str__(self):
        return f"{self.lesson.title} — {self.question[:50]}"


class ReadingActivity(models.Model):
    """A grade-calibrated comprehension activity for one story."""

    MULTIPLE_CHOICE = 'multiple_choice'
    TRUE_FALSE = 'true_false'
    OPEN_ENDED = 'open_ended'
    SEQUENCING = 'sequencing'
    MATCHING = 'matching'
    CLOZE = 'cloze'
    ORAL_RESPONSE = 'oral_response'
    PREDICTION = 'prediction'
    REASONING = 'reasoning'
    CROSSWORD = 'crossword'
    WORD_SCRAMBLE = 'word_scramble'

    ACTIVITY_TYPES = [
        (MULTIPLE_CHOICE, 'Multiple choice'),
        (TRUE_FALSE, 'True or false'),
        (OPEN_ENDED, 'Open-ended response'),
        (SEQUENCING, 'Sequencing'),
        (MATCHING, 'Matching'),
        (CLOZE, 'Fill in the blank'),
        (ORAL_RESPONSE, 'Oral response'),
        (PREDICTION, 'Prediction'),
        (REASONING, 'Reasoning'),
        (CROSSWORD, 'Crossword puzzle'),
        (WORD_SCRAMBLE, 'Word scramble'),
    ]

    SKILL_CHOICES = [
        ('literal_comprehension', 'Literal comprehension'),
        ('sequencing', 'Sequencing'),
        ('inference', 'Inference'),
        ('vocabulary_in_context', 'Vocabulary in context'),
        ('prediction', 'Prediction'),
        ('summarising', 'Summarising'),
        ('character_motivation', 'Character motivation'),
        ('text_to_self', 'Text-to-self connection'),
        ('fact_vs_opinion', 'Fact versus opinion'),
        ('spelling', 'Spelling'),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='reading_activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    skill = models.CharField(max_length=40, choices=SKILL_CHOICES)
    question = models.TextField()
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.TextField(blank=True)
    items_in_correct_order = models.JSONField(default=list, blank=True)
    order = models.PositiveIntegerField(default=0)
    group_number = models.PositiveSmallIntegerField(default=0)
    group_title = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ['order', 'id']

    @property
    def requires_review(self):
        return self.activity_type in {
            self.OPEN_ENDED,
            self.ORAL_RESPONSE,
            self.PREDICTION,
            self.REASONING,
        }

    def get_options(self):
        if self.activity_type == self.TRUE_FALSE and not self.options:
            return ['True', 'False']
        if isinstance(self.options, dict):
            return dict(self.options)
        return list(self.options or [])

    def __str__(self):
        return f"{self.lesson.title} - {self.get_activity_type_display()}: {self.question[:50]}"


class ReadingActivityResponse(models.Model):
    """Stores a learner's guided writing response for a story."""

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='reading_responses')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='learner_responses')
    activity = models.ForeignKey(
        ReadingActivity,
        on_delete=models.SET_NULL,
        related_name='learner_responses',
        null=True,
        blank=True,
    )
    response = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['child', 'lesson'],
                name='unique_child_lesson_reading_response',
            ),
        ]

    def __str__(self):
        return f"{self.child.name} - {self.lesson.title} response"


class VisualActivityItem(models.Model):
    """One image-word pair in the visual matching activity."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='visual_items')
    image_url = models.CharField(max_length=300, blank=True)
    correct_word = models.CharField(max_length=100)
    # Stored as comma-separated values e.g. "Apple,Banana,Orange,Mango"
    word_options = models.TextField()

    def get_word_options(self):
        return [w.strip() for w in self.word_options.split(',')]

    def __str__(self):
        return f"{self.lesson.title} — {self.correct_word}"


class PronunciationWord(models.Model):
    """A word with English + isiZulu audio for the phonics screen."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='pronunciation_words')
    word = models.CharField(max_length=100)
    image_url = models.CharField(max_length=300, blank=True)
    english_audio = models.CharField(max_length=300, blank=True)
    isizulu_audio = models.CharField(max_length=300, blank=True)
    isizulu_word = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.lesson.title} — {self.word} / {self.isizulu_word}"


class SpellingActivity(models.Model):
    """One of the three spelling exercise types."""
    FILL_VOWEL = 'fill-missing-vowel'
    DRAG_LETTERS = 'drag-letters'
    COPY_WRITING = 'copy-writing'

    ACTIVITY_TYPES = [
        (FILL_VOWEL, 'Fill Missing Vowel'),
        (DRAG_LETTERS, 'Drag Letters'),
        (COPY_WRITING, 'Copy Writing'),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='spelling_activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    # For fill-vowel: "B_nana"  |  drag-letters: "R,A,N,O,G,E"  |  copy-writing: full sentence
    display_text = models.CharField(max_length=300, blank=True)
    answer = models.CharField(max_length=300)
    image_url = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"{self.lesson.title} — {self.activity_type}"


class Progress(models.Model):
    """Saves a child's scores after completing a lesson."""
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='progress_records')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress_records')
    comprehension_score = models.IntegerField(default=0)
    visual_score = models.IntegerField(default=0)
    spelling_score = models.IntegerField(default=0)
    total_score = models.IntegerField(default=0)
    total_possible = models.IntegerField(default=0)
    stars_earned = models.IntegerField(default=0)
    assessment_scores = models.JSONField(default=dict, blank=True)
    completed_on = models.DateTimeField(auto_now_add=True)

    @property
    def percentage(self):
        if self.total_possible == 0:
            return 0
        return round((self.total_score / self.total_possible) * 100)

    def __str__(self):
        return f"{self.child.name} — {self.lesson.title} — {self.stars_earned} stars"


class VocabularyQuestion(models.Model):
    """Match a word to its meaning — used in Grade 4 vocabulary activity."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='vocabulary_questions')
    word = models.CharField(max_length=100)
    option_1 = models.CharField(max_length=200)
    option_2 = models.CharField(max_length=200)
    option_3 = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=200)

    def get_options(self):
        return [self.option_1, self.option_2, self.option_3]

    def __str__(self):
        return f"{self.lesson.title} — vocab: {self.word}"


class SequencingActivity(models.Model):
    """A set of events to be placed in the correct story order."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='sequencing_activities')
    # Comma-separated events in CORRECT order, e.g. "Event A|Event B|Event C"
    ordered_events = models.TextField()
    instruction = models.CharField(max_length=300, default='Put these events in the correct order.')

    def get_events_in_order(self):
        return [e.strip() for e in self.ordered_events.split('|')]

    def __str__(self):
        return f"{self.lesson.title} — sequencing"


class InferenceQuestion(models.Model):
    """Read-between-the-lines multiple-choice question."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='inference_questions')
    question = models.TextField()
    option_1 = models.CharField(max_length=200)
    option_2 = models.CharField(max_length=200)
    option_3 = models.CharField(max_length=200)
    option_4 = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=200)

    def get_options(self):
        return [self.option_1, self.option_2, self.option_3, self.option_4]

    def __str__(self):
        return f"{self.lesson.title} — inference: {self.question[:50]}"


class PredictionQuestion(models.Model):
    """Shown mid-story at a stop point; learner predicts what happens next."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='prediction_questions')
    stop_point_text = models.TextField(help_text="The story line after which the question appears.")
    question = models.CharField(max_length=300, default='What do you think will happen next?')
    option_1 = models.CharField(max_length=200)
    option_2 = models.CharField(max_length=200)
    option_3 = models.CharField(max_length=200)
    option_4 = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=200)

    def get_options(self):
        return [self.option_1, self.option_2, self.option_3, self.option_4]

    def __str__(self):
        return f"{self.lesson.title} — prediction"


class FeelingsQuestion(models.Model):
    """Emotional literacy — how did a character feel?"""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='feelings_questions')
    question = models.TextField()
    option_1 = models.CharField(max_length=100)
    option_2 = models.CharField(max_length=100)
    option_3 = models.CharField(max_length=100)
    option_4 = models.CharField(max_length=100)
    correct_answer = models.CharField(max_length=100)

    def get_options(self):
        return [self.option_1, self.option_2, self.option_3, self.option_4]

    def __str__(self):
        return f"{self.lesson.title} — feelings: {self.question[:50]}"


class CauseEffectPair(models.Model):
    """One cause-and-effect pair for a matching activity."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='cause_effect_pairs')
    cause = models.TextField()
    effect = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.lesson.title} — cause: {self.cause[:40]}"


class ThemeQuestion(models.Model):
    """Higher-order thinking — what is the main lesson/theme of the story?"""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='theme_questions')
    question = models.CharField(max_length=300, default='What is the main lesson of the story?')
    option_1 = models.CharField(max_length=200)
    option_2 = models.CharField(max_length=200)
    option_3 = models.CharField(max_length=200)
    option_4 = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=200)

    def get_options(self):
        return [self.option_1, self.option_2, self.option_3, self.option_4]

    def __str__(self):
        return f"{self.lesson.title} — theme"


class Grade4ActivityProgress(models.Model):
    """
    Stores per-activity scores for a Grade 4 lesson attempt.
    Each row captures one child's result for one lesson.
    The six seeded activities map to the six score fields below.
    """
    child = models.ForeignKey('Child', on_delete=models.CASCADE, related_name='g4_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='g4_progress')
    completed_on = models.DateTimeField(auto_now_add=True)

    # Activity 1 — Comprehension Questions
    comprehension_score = models.IntegerField(default=0)
    comprehension_total = models.IntegerField(default=0)

    # Activity 2 — Sequencing
    sequencing_score = models.IntegerField(default=0)
    sequencing_total = models.IntegerField(default=0)

    # Activity 3 — Inference
    inference_score = models.IntegerField(default=0)
    inference_total = models.IntegerField(default=0)

    # Activity 4 — Feelings / Emotional Literacy
    feelings_score = models.IntegerField(default=0)
    feelings_total = models.IntegerField(default=0)

    # Activity 5 — Cause & Effect
    cause_effect_score = models.IntegerField(default=0)
    cause_effect_total = models.IntegerField(default=0)

    # Activity 6 — Theme / Main Lesson
    theme_score = models.IntegerField(default=0)
    theme_total = models.IntegerField(default=0)

    # Overall
    total_score = models.IntegerField(default=0)
    total_possible = models.IntegerField(default=0)
    stars_earned = models.IntegerField(default=0)

    @property
    def percentage(self):
        if self.total_possible == 0:
            return 0
        return round((self.total_score / self.total_possible) * 100)

    def activity_scores(self):
        """Return list of (label, score, total, pct) sorted best → worst."""
        rows = [
            ('Comprehension', self.comprehension_score, self.comprehension_total),
            ('Sequencing',    self.sequencing_score,    self.sequencing_total),
            ('Inference',     self.inference_score,     self.inference_total),
            ('Feelings',      self.feelings_score,      self.feelings_total),
            ('Cause & Effect',self.cause_effect_score,  self.cause_effect_total),
            ('Main Lesson',   self.theme_score,         self.theme_total),
        ]
        return sorted(
            [{'label': l, 'score': s, 'total': t,
              'pct': round((s / t) * 100) if t else 0}
             for l, s, t in rows],
            key=lambda x: x['pct'],
            reverse=True,
        )

    class Meta:
        ordering = ['-completed_on']

    def __str__(self):
        return f"{self.child.name} — {self.lesson.title} (G4) — {self.stars_earned}★"


class WrittenResponsePrompt(models.Model):
    """Open-ended written response prompt for higher-level learners."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='written_prompts')
    prompt = models.TextField()
    guidance = models.CharField(max_length=300, blank=True, help_text="E.g. 'Write 3 to 4 sentences.'")

    def __str__(self):
        return f"{self.lesson.title} — written prompt"


class PackageCode(models.Model):
    """
    A redemption code issued to a government/district after they buy a
    school package. Sgila staff create these (via admin); a school then
    redeems one on the enterprise plan screen with just their school name
    and this code — no card, no per-family payment.
    """
    code = models.CharField(max_length=32, unique=True)
    label = models.CharField(max_length=160, blank=True)  # e.g. "KZN Rural Schools Batch — 2026"
    max_redemptions = models.PositiveIntegerField(default=1)
    redemptions_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.redemptions_count}/{self.max_redemptions})"

    @property
    def is_redeemable(self):
        return self.is_active and self.redemptions_count < self.max_redemptions


class Subscription(models.Model):
    """
    Tracks the subscription for a parent (individual/family plan) or a
    school (enterprise plan, redeemed with a government-issued package
    code rather than paid card-by-card).
    """
    PLAN_CHOICES = [
        ('individual', 'Individual (Parent)'),
        ('family', 'Family (Parent)'),
        ('enterprise', 'Enterprise (School)'),
    ]
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]
    STATUS_CHOICES = [
        ('trial', 'Free trial'),
        ('pending', 'Pending — awaiting payment/approval'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
    ]

    parent = models.OneToOneField(
        Parent, on_delete=models.CASCADE, null=True, blank=True, related_name='subscription',
    )
    teacher = models.OneToOneField(
        Teacher, on_delete=models.CASCADE, null=True, blank=True, related_name='subscription',
    )

    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES)
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='trial')

    # Enterprise / government-package redemption.
    school_name = models.CharField(max_length=200, blank=True)
    package_code = models.ForeignKey(
        PackageCode, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions',
    )
    district_or_province = models.CharField(max_length=160, blank=True)
    estimated_learners = models.IntegerField(null=True, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    funding_source = models.CharField(max_length=160, blank=True)  # e.g. "Dept of Basic Education - KZN"
    notes = models.TextField(blank=True)

    # --- Payment summary (individual plan) --------------------------------
    # IMPORTANT: only ever store a non-sensitive SUMMARY here — never a full
    # card/account number, CVV, or expiry-with-CVV combo. Full card/bank
    # details must go straight to a PCI-compliant gateway (e.g. PayFast),
    # not through this database. See subscription_payment_page in views.py.
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Debit/Credit card'),
        ('debit_order', 'Bank debit order'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payer_name = models.CharField(max_length=120, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_expiry = models.CharField(max_length=7, blank=True)  # "MM/YYYY", no CVV ever stored
    bank_name = models.CharField(max_length=80, blank=True)
    account_last4 = models.CharField(max_length=4, blank=True)
    branch_code = models.CharField(max_length=10, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Free trial window, counted from created_at (the moment the subscription
    # row was first created, i.e. the moment the trial started).
    TRIAL_DAYS = 30

    def __str__(self):
        owner = self.parent or self.teacher
        return f"{self.get_plan_type_display()} - {owner} ({self.status})"

    def save(self, *args, **kwargs):
        self.school_name = title_case(self.school_name)
        for field in ('district_or_province', 'contact_name', 'funding_source', 'notes', 'payer_name', 'bank_name'):
            setattr(self, field, capitalize_first(getattr(self, field)))
        super().save(*args, **kwargs)

    @property
    def trial_ends_at(self):
        """The datetime the 30-day free trial lapses, counted from created_at."""
        from datetime import timedelta
        return self.created_at + timedelta(days=self.TRIAL_DAYS)

    @property
    def is_trial_expired(self):
        """True once a subscription still sitting in 'trial' status has passed
        its 30-day window. Subscriptions that have moved to 'active' (paid),
        'pending' (school awaiting approval), or 'cancelled' are never
        considered trial-expired here — enterprise/school subscriptions are
        redeemed via a package code straight into 'active', so this only ever
        bites individual/family plans that haven't paid.
        """
        if self.status != 'trial':
            return False
        return timezone.now() >= self.trial_ends_at

    @property
    def trial_days_left(self):
        """Whole days left in the trial, floored at 0. None if not on trial."""
        if self.status != 'trial':
            return None
        remaining = self.trial_ends_at - timezone.now()
        return max(0, remaining.days)


class OTPToken(models.Model):
    """Stores a one-time password for email verification after registration."""
    ROLE_CHOICES = [('parent', 'Parent'), ('teacher', 'Teacher')]

    email = models.EmailField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)
    pending_data = models.TextField(blank=True)  # JSON of registration data waiting for verification

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        """OTP expires after 10 minutes."""
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.email} ({'used' if self.is_used else 'active'})"


class PasswordResetToken(models.Model):
    """One-time token for resetting a parent or teacher password via email."""
    ROLE_CHOICES = [('parent', 'Parent'), ('teacher', 'Teacher')]

    email = models.EmailField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        """Token expires after 30 minutes."""
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(minutes=30)

    def __str__(self):
        return f"PasswordReset for {self.email} ({'used' if self.is_used else 'active'})"


class AccountActionOTP(models.Model):
    """A short-lived, single-purpose OTP for sensitive account actions.

    Belongs to either a parent or a teacher (never both) — see `account`.
    """

    REACTIVATE_PARENT = 'reactivate_parent'
    REACTIVATE_TEACHER = 'reactivate_teacher'
    ACTION_CHOICES = [
        (REACTIVATE_PARENT, 'Reactivate parent account'),
        (REACTIVATE_TEACHER, 'Reactivate teacher account'),
    ]
    MAX_ATTEMPTS = 5

    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='account_action_otps',
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='account_action_otps',
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    code_hash = models.CharField(max_length=300)
    created_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    @property
    def can_attempt(self):
        return not self.is_used and not self.is_expired() and self.attempts < self.MAX_ATTEMPTS

    @property
    def account(self):
        return self.parent or self.teacher

    def __str__(self):
        return f"{self.get_action_display()} for {self.account.email if self.account else 'unknown'}"


# ─────────────────────────────────────────────
#  MESSAGING — Parent ↔ Teacher per learner
# ─────────────────────────────────────────────

class Message(models.Model):
    """A single chat message between a parent and a teacher about a specific child."""

    SENDER_CHOICES = [('parent', 'Parent'), ('teacher', 'Teacher')]

    child = models.ForeignKey(
        Child, on_delete=models.CASCADE, related_name='messages',
        help_text="The learner this conversation is about."
    )
    sender_role = models.CharField(max_length=10, choices=SENDER_CHOICES)
    sender_parent = models.ForeignKey(
        Parent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_messages'
    )
    sender_teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_messages'
    )
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        sender = self.sender_parent or self.sender_teacher
        return f"Message about {self.child.name} from {self.sender_role} ({sender}) at {self.sent_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        self.body = capitalize_first(self.body)
        super().save(*args, **kwargs)


# ───────────── AI story generation (background job tracking) ─────────────

class AIStoryJob(models.Model):
    """Tracks one background 'write me a new story' request for a learner.

    Generation (Gemini text + Pollinations illustrations) happens in a
    background thread so the HTTP request that kicks it off can return
    immediately; the frontend polls this row's status instead of blocking
    on the request. Coordination is via the database, not shared memory,
    so this also works correctly across multiple web-server processes.
    """

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_DONE = 'done'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_DONE, 'Done'),
        (STATUS_ERROR, 'Error'),
    ]

    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='ai_story_jobs')
    grade = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    lesson = models.ForeignKey(
        Lesson, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ai_story_job',
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AI story job for {self.child.name} (grade {self.grade}) — {self.status}"
