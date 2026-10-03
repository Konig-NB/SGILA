"""
SGILA API URL PATTERNS
Every endpoint from the API contract is listed here with a comment
showing which screen it belongs to and the HTTP method.
"""
from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter
from .help_center_views import FeedbackViewSet, HelpArticleViewSet, HelpCategoryViewSet, SupportTicketViewSet

help_router = DefaultRouter()
help_router.register('help/categories', HelpCategoryViewSet, basename='help-category')
help_router.register('help/articles', HelpArticleViewSet, basename='help-article')
help_router.register('help/tickets', SupportTicketViewSet, basename='help-ticket')
help_router.register('help/feedback', FeedbackViewSet, basename='help-feedback')

urlpatterns = [
    path('schools/search/', views.school_search, name='school-search'),

    # Screen 2 — Registration
    path('register', views.register, name='register'),

    # OTP Verification (Step 2: verify code + create account + return JWT)
    path('verify-otp', views.verify_otp, name='verify-otp'),

    # Resend OTP
    path('resend-otp', views.resend_otp, name='resend-otp'),

    # Screen 3 — Login (returns JWT)
    path('login', views.login, name='login'),

    # Forgot / Reset Password
    path('forgot-password', views.forgot_password, name='forgot-password'),
    path('reset-password', views.reset_password, name='reset-password'),

    # Screen 4 — Grade Home Page  e.g. GET /api/lessons?grade=1
    path('lessons', views.lesson_list, name='lesson-list'),

    # Screen 5 — Story            e.g. GET /api/lessons/1/story
    path('lessons/<int:lesson_id>/story', views.story, name='story'),

    # Screen 6A — Questions       e.g. GET /api/lessons/1/questions
    path('lessons/<int:lesson_id>/questions', views.questions, name='questions'),

    # Screen 6B — Check Answer    POST /api/check-answer
    path('check-answer', views.check_answer, name='check-answer'),
    path('check-reading-activity', views.check_reading_activity, name='check-reading-activity'),

    # Screen 7 — Visual Activity  e.g. GET /api/lessons/1/visual-activity
    path('lessons/<int:lesson_id>/visual-activity', views.visual_activity, name='visual-activity'),
    path('check-visual-answer', views.check_visual_answer, name='check-visual-answer'),

    # Screen 8 — Pronunciation    e.g. GET /api/lessons/1/pronunciation
    path('lessons/<int:lesson_id>/pronunciation', views.pronunciation, name='pronunciation'),

    # Screen 9 — Spelling         e.g. GET /api/lessons/1/spelling
    path('lessons/<int:lesson_id>/spelling', views.spelling, name='spelling'),
    path('check-spelling-answer', views.check_spelling_answer, name='check-spelling-answer'),

    # Screen 10 — Save Progress   POST /api/progress
    path('progress', views.save_progress, name='save-progress'),

    # Screen 11 — Dashboard       e.g. GET /api/progress/1
    path('progress/<int:child_id>', views.get_progress, name='get-progress'),

    # Grade 4 Activities
    path('lessons/<int:lesson_id>/vocabulary', views.vocabulary_activity, name='vocabulary-activity'),
    path('check-vocabulary-answer', views.check_vocabulary_answer, name='check-vocabulary-answer'),

    path('lessons/<int:lesson_id>/sequencing', views.sequencing_activity, name='sequencing-activity'),
    path('check-sequencing-answer', views.check_sequencing_answer, name='check-sequencing-answer'),

    path('lessons/<int:lesson_id>/inference', views.inference_activity, name='inference-activity'),
    path('check-inference-answer', views.check_inference_answer, name='check-inference-answer'),

    path('lessons/<int:lesson_id>/prediction', views.prediction_activity, name='prediction-activity'),
    path('check-prediction-answer', views.check_prediction_answer, name='check-prediction-answer'),

    path('lessons/<int:lesson_id>/feelings', views.feelings_activity, name='feelings-activity'),
    path('check-feelings-answer', views.check_feelings_answer, name='check-feelings-answer'),

    path('lessons/<int:lesson_id>/cause-effect', views.cause_effect_activity, name='cause-effect-activity'),
    path('check-cause-effect-answer', views.check_cause_effect_answer, name='check-cause-effect-answer'),

    path('lessons/<int:lesson_id>/theme', views.theme_activity, name='theme-activity'),
    path('check-theme-answer', views.check_theme_answer, name='check-theme-answer'),

    path('lessons/<int:lesson_id>/written-response', views.written_response_activity, name='written-response-activity'),

    # ── Messaging — Parent ↔ Teacher ─────────────────────────────────────────
    path('messages/unread-count', views.unread_messages_count, name='messages-unread-count'),
    path('messages/<int:child_id>', views.get_messages, name='get-messages'),
    path('messages/<int:child_id>/send', views.send_message, name='send-message'),
] + help_router.urls
