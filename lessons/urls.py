from django.urls import path
from . import views

urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('terms', views.terms_page, name='terms'),
    path('ui-flow', views.ui_flow_diagram, name='ui-flow-diagram'),
    path('download/ui-flow-pdf', views.download_ui_flow_pdf, name='download-ui-flow-pdf'),
    path('register', views.register_page, name='register-page'),
    path('login', views.login_page, name='login-page'),
    path('logout', views.logout_view, name='logout'),
    path('forgot-password', views.forgot_password_page, name='forgot-password'),
    path('reset-password', views.reset_password_page, name='reset-password'),
    path('verify-otp', views.verify_otp_page, name='verify-otp'),
    path('subscription', views.subscription_page, name='subscription-page'),
    path('subscription/payment', views.subscription_payment_page, name='subscription-payment-page'),
    path('subscription/cancel', views.subscription_cancel_page, name='subscription-cancel-page'),
    path('parent/dashboard', views.parent_dashboard, name='parent-dashboard'),
    path('parent/add-child', views.parent_add_child, name='parent-add-child'),
    path('parent/delete-child/<int:child_id>', views.parent_delete_child, name='parent-delete-child'),
    path('teacher/dashboard', views.teacher_dashboard, name='teacher-dashboard'),
    path('confirm-grade/<int:child_id>', views.confirm_child_grade, name='confirm-child-grade'),
    path('grade/<int:grade>', views.grade_home, name='grade-home'),
    path('grade/<int:grade>/generate-ai-story', views.generate_ai_story_ajax, name='generate-ai-story'),
    path('ai-story-job/<int:job_id>/status', views.ai_story_job_status, name='ai-story-job-status'),
    path('lessons/<int:lesson_id>/story', views.story_page, name='story-page'),
    path('lessons/<int:lesson_id>/questions', views.questions_page, name='questions-page'),
    path('lessons/<int:lesson_id>/visual-activity', views.visual_activity_page, name='visual-activity-page'),
    path('lessons/<int:lesson_id>/pronunciation', views.pronunciation_page, name='pronunciation-page'),
    path('lessons/<int:lesson_id>/spelling', views.spelling_page, name='spelling-page'),
    path('lessons/<int:lesson_id>/results', views.results_page, name='results-page'),
    path('dashboard/<int:child_id>', views.dashboard_page, name='dashboard'),
    path(
        'dashboard/<int:child_id>/lessons/<int:lesson_id>',
        views.story_report_page,
        name='story-report',
    ),

    # Grade 4 activity pages
    path('lessons/<int:lesson_id>/vocabulary', views.vocabulary_page, name='vocabulary-page'),
    path('lessons/<int:lesson_id>/sequencing', views.sequencing_page, name='sequencing-page'),
    path('lessons/<int:lesson_id>/inference', views.inference_page, name='inference-page'),
    path('lessons/<int:lesson_id>/prediction', views.prediction_page, name='prediction-page'),
    path('lessons/<int:lesson_id>/feelings', views.feelings_page, name='feelings-page'),
    path('lessons/<int:lesson_id>/cause-effect', views.cause_effect_page, name='cause-effect-page'),
    path('lessons/<int:lesson_id>/theme', views.theme_page, name='theme-page'),
    path('lessons/<int:lesson_id>/written-response', views.written_response_page, name='written-response-page'),

    # ── Messaging — Parent ↔ Teacher ────────────────────────────────────────
    path('conversations', views.conversations_page, name='conversations'),
    path('messages/<int:child_id>', views.chat_page, name='chat-page'),
]
