from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve


class ActivityAudioTemplateTests(SimpleTestCase):
    def test_activity_audio_has_word_boundary_highlighting(self):
        template = (Path(settings.BASE_DIR) / 'templates' / 'questions.html').read_text(
            encoding='utf-8'
        )
        self.assertIn("word.className = 'activity-speech-word'", template)
        self.assertIn('utterance.onboundary', template)
        self.assertIn('highlightActivityWord(words, event.charIndex)', template)
        self.assertIn("isPhonicsWord ? config.audio_text : activity.question", template)


class ParentDashboardChildDeletionTests(SimpleTestCase):
    def test_parent_dashboard_has_no_child_delete_control(self):
        template = (Path(settings.BASE_DIR) / 'templates' / 'parent_dashboard.html').read_text(
            encoding='utf-8'
        )
        self.assertNotIn('/parent/delete-child/', template)
        self.assertNotIn('Delete this learner profile permanently', template)

    def test_child_delete_route_is_not_registered(self):
        with self.assertRaises(Resolver404):
            resolve('/parent/delete-child/1')
