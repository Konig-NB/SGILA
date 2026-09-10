"""
Django Admin configuration for Sgila.
Register all models here so the admin can add/edit content 
without writing code.
"""
from django.contrib import admin
from django.utils.crypto import get_random_string

from .models import (
    Parent, Teacher, Child, Lesson, StoryPage, ComprehensionQuestion, ReadingActivity,
    VisualActivityItem, PronunciationWord, SpellingActivity, Progress,
    TeacherClass, Message, Subscription, PackageCode, AIStoryJob, GradeHistory,
    AccountActionOTP,
)

@admin.register(PackageCode)
class PackageCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'label', 'redemptions_count', 'max_redemptions', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'label')
    readonly_fields = ('redemptions_count', 'created_at')

    def save_model(self, request, obj, form, change):
        if not obj.code:
            obj.code = get_random_string(10).upper()
        super().save_model(request, obj, form, change)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'plan_type', 'status', 'billing_cycle', 'payment_summary', 'school_name', 'package_code', 'created_at')
    list_filter = ('plan_type', 'status', 'billing_cycle', 'payment_method')
    search_fields = ('parent__full_name', 'parent__email', 'teacher__full_name', 'school_name', 'district_or_province')

    def payment_summary(self, obj):
        if obj.payment_method == 'card' and obj.card_last4:
            return f"Card •••• {obj.card_last4} ({obj.card_expiry})"
        if obj.payment_method == 'debit_order' and obj.account_last4:
            return f"{obj.bank_name} •••• {obj.account_last4}"
        return "—"
    payment_summary.short_description = 'Payment method'


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'grade', 'is_ai_generated', 'generated_for', 'created_at')
    list_filter = ('grade', 'is_ai_generated')
    search_fields = ('title',)


@admin.register(AIStoryJob)
class AIStoryJobAdmin(admin.ModelAdmin):
    list_display = ('child', 'grade', 'status', 'lesson', 'created_at', 'updated_at')
    list_filter = ('status', 'grade')
    search_fields = ('child__name',)
    readonly_fields = ('created_at', 'updated_at')


class StoryPageInline(admin.TabularInline):
    model = StoryPage
    extra = 1


class QuestionInline(admin.TabularInline):
    model = ComprehensionQuestion
    extra = 1


@admin.register(StoryPage)
class StoryPageAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'page_number')
    list_filter = ('lesson',)


@admin.register(ComprehensionQuestion)
class ComprehensionQuestionAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'question', 'correct_answer')
    list_filter = ('lesson',)


@admin.register(ReadingActivity)
class ReadingActivityAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'order', 'activity_type', 'skill', 'question')
    list_filter = ('lesson', 'activity_type', 'skill')
    ordering = ('lesson', 'order')


@admin.register(VisualActivityItem)
class VisualActivityItemAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'correct_word')


@admin.register(PronunciationWord)
class PronunciationWordAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'word', 'isizulu_word')


@admin.register(SpellingActivity)
class SpellingActivityAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'activity_type', 'answer')


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('name', 'username', 'grade', 'grade_confirmed_year', 'school_name', 'parent_email', 'parent', 'teacher', 'teacher_class', 'created_at')
    list_filter = ('grade', 'school_name')
    search_fields = ('name', 'username', 'parent_email', 'school_name')


@admin.register(GradeHistory)
class GradeHistoryAdmin(admin.ModelAdmin):
    list_display = ('child', 'year', 'grade', 'repeated', 'confirmed_by', 'confirmed_by_name', 'created_at')
    list_filter = ('year', 'grade', 'repeated', 'confirmed_by')
    search_fields = ('child__name', 'confirmed_by_name')
    readonly_fields = ('created_at',)
    ordering = ('-year', 'child__name')


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'is_active', 'deactivated_at', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('full_name', 'email', 'phone')


@admin.register(AccountActionOTP)
class AccountActionOTPAdmin(admin.ModelAdmin):
    list_display = ('parent', 'action', 'created_at', 'attempts', 'is_used')
    list_filter = ('action', 'is_used')
    search_fields = ('parent__full_name', 'parent__email')
    readonly_fields = ('parent', 'action', 'code_hash', 'created_at', 'attempts', 'is_used')

    def has_add_permission(self, request):
        return False


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'school_name', 'grades_taught', 'class_code', 'created_at')
    list_filter = ('school_name',)
    search_fields = ('full_name', 'email', 'school_name', 'class_code')


@admin.register(TeacherClass)
class TeacherClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade', 'teacher', 'class_code', 'created_at')
    list_filter = ('grade', 'teacher')
    search_fields = ('name', 'class_code', 'teacher__full_name')


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('child', 'lesson', 'total_score', 'total_possible', 'stars_earned', 'completed_on')
    list_filter = ('stars_earned', 'lesson')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('child', 'sender_role', 'sender_name_display', 'body_preview', 'sent_at', 'is_read')
    list_filter = ('sender_role', 'is_read', 'sent_at')
    search_fields = ('child__name', 'sender_parent__full_name', 'sender_teacher__full_name', 'body')
    readonly_fields = ('sent_at',)
    ordering = ('-sent_at',)

    def sender_name_display(self, obj):
        if obj.sender_role == 'parent' and obj.sender_parent:
            return obj.sender_parent.full_name
        if obj.sender_role == 'teacher' and obj.sender_teacher:
            return obj.sender_teacher.full_name
        return '—'
    sender_name_display.short_description = 'Sender'

    def body_preview(self, obj):
        return obj.body[:60] + ('…' if len(obj.body) > 60 else '')
    body_preview.short_description = 'Message'
