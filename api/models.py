import random
import string

from django.db import models
from django.utils import timezone


def generate_class_code():
    """Generate a short teacher/class code for parent and learner linking."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class Parent(models.Model):
    """Guardian account that can manage one or more learner profiles."""
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=300)
    phone = models.CharField(max_length=30, blank=True)
    accepted_popia = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Child(models.Model):
    """Stores every registered child in the app."""
    parent = models.ForeignKey(Parent, on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='learners')
    teacher_class = models.ForeignKey('TeacherClass', on_delete=models.SET_NULL, null=True, blank=True, related_name='learners')
    username = models.CharField(max_length=40, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    grade = models.IntegerField()          # 1 to 4
    school_name = models.CharField(max_length=160, blank=True)
    parent_email = models.EmailField()
    photo = models.FileField(upload_to='child_photos/', blank=True)
    password = models.CharField(max_length=300)   # hashed by Django
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Grade {self.grade})"


class TeacherClass(models.Model):
    """Named class/group owned by a teacher and joined through a class code."""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='classes')
    name = models.CharField(max_length=80)
    grade = models.IntegerField(default=1)
    class_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['grade', 'name']

    def __str__(self):
        return f"{self.teacher.full_name} - {self.name}"


class Lesson(models.Model):
    """One lesson card shown on the home page."""
    title = models.CharField(max_length=200)
    grade = models.IntegerField()
    thumbnail_image = models.CharField(max_length=300, blank=True)
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
