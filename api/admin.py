"""
Django Admin configuration for Sgila.
Register all models here so the admin can add/edit content 
without writing code.
"""
from django.contrib import admin
from .models import (
    Parent, Teacher, Child, Lesson, StoryPage, ComprehensionQuestion,
    VisualActivityItem, PronunciationWord, SpellingActivity, Progress,
    TeacherClass, Message,
)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'grade', 'created_at')
    list_filter = ('grade',)
    search_fields = ('title',)


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
    list_display = ('name', 'username', 'grade', 'school_name', 'parent_email', 'parent', 'teacher', 'teacher_class', 'created_at')
    list_filter = ('grade', 'school_name')
    search_fields = ('name', 'username', 'parent_email', 'school_name')


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'created_at')
    search_fields = ('full_name', 'email', 'phone')


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
