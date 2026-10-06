from django.contrib import admin

from schools.models import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'province',
        'district',
        'quintile',
        'sector',
        'status',
        'learners_2025',
    )
    list_filter = ('province', 'sector', 'status', 'quintile')
    search_fields = ('name', 'emis_number', 'town', 'district')
    ordering = ('name',)