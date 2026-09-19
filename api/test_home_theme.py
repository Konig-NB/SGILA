from pathlib import Path

from django.test import SimpleTestCase


class HomeThemeTests(SimpleTestCase):
    def test_homepage_uses_shared_toggle_and_current_stylesheet(self):
        response = self.client.get('/')

        self.assertContains(response, 'class="home-page"')
        self.assertContains(response, 'id="theme-toggle"')
        self.assertContains(response, "localStorage.setItem('sgila-theme', 'dark')")
        self.assertContains(response, 'css/sgila_app.css')
        self.assertNotContains(response, 'css/sgila.css')

    def test_homepage_uses_grade_one_covers_and_simple_role_buttons(self):
        response = self.client.get('/')
        html = response.content.decode('utf-8')

        for cover in (
            'g1_lerato_fruit_basket.webp',
            'g1_very_hot_day.webp',
            'g1_ben_goes_to_school.webp',
            'g1_olwethu_first_day.webp',
            'g1_bongi_waits.webp',
        ):
            self.assertIn(cover, html)
        self.assertIn('home_reading_studio_v2.png', html)
        self.assertEqual(html.count('class="studio-story-card"'), 5)
        self.assertNotIn("I'm a parent or teacher", html)
        self.assertNotIn('studio-role-mark', html)
        for label in ('Learner', 'Parent', 'Teacher'):
            self.assertIn(f'<span>{label}</span>', html)

    def test_homepage_read_listen_understand_and_role_styles(self):
        css_path = Path(__file__).resolve().parent.parent / 'static' / 'css' / 'sgila_app.css'
        css = css_path.read_text(encoding='utf-8')

        self.assertIn('.studio-kicker-read {\n  color: #ffd22e;', css)
        self.assertIn('.studio-kicker-listen {\n  color: #83a8f6;', css)
        self.assertIn('.studio-kicker-understand {\n  color: #5bdad4;', css)
        self.assertIn('.studio-kicker-slash {\n  color: #14213d;', css)
        self.assertIn('gap: 10px;', css)
        self.assertNotIn('box-shadow: inset 0 -4px #14213d;', css)

    def test_homepage_has_distinct_dark_palette_without_changing_role_colours(self):
        css_path = Path(__file__).resolve().parent.parent / 'static' / 'css' / 'sgila_app.css'
        css = css_path.read_text(encoding='utf-8')

        self.assertIn('[data-theme="dark"] body.home-page {', css)
        self.assertIn('--studio-library: #16323f;', css)
        self.assertIn('--studio-ink: #f4f7ff;', css)
        self.assertIn('background: var(--studio-library);', css)
        self.assertIn('color: var(--studio-ink);', css)
        self.assertIn('background: #ffd22e;', css)
        self.assertIn('background: #83a8f6;', css)
        self.assertIn('background: #5bdad4;', css)
        self.assertIn('[data-theme="dark"] .studio-kicker-slash {', css)
        self.assertIn('background: transparent;', css)
        self.assertIn('color: var(--studio-muted);', css)
        self.assertIn('box-shadow: 0 0 0 5px rgba(var(--surface-rgb),.92), 0 8px 18px rgba(72, 86, 112, .16);', css)
        self.assertNotIn('box-shadow: 0 0 0 5px rgba(255,255,255,.92), 0 8px 18px rgba(72, 86, 112, .16);', css)
        self.assertEqual(css.count('{'), css.count('}'))
