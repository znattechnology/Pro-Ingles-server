from django.contrib import admin
from .models import (
    PracticeUnit, 
    PracticeLesson, 
    PracticeChallenge, 
    ChallengeOption, 
    UserProgress, 
    ChallengeProgress
)


class ChallengeOptionInline(admin.TabularInline):
    model = ChallengeOption
    extra = 0
    fields = ['text', 'is_correct', 'image_url', 'audio_url', 'order']


class PracticeChallengeInline(admin.TabularInline):
    model = PracticeChallenge
    extra = 0
    fields = ['type', 'question', 'order']


class PracticeLessonInline(admin.TabularInline):
    model = PracticeLesson
    extra = 0
    fields = ['title', 'order']


@admin.register(PracticeUnit)
class PracticeUnitAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['title', 'description']
    inlines = [PracticeLessonInline]
    ordering = ['course', 'order']


@admin.register(PracticeLesson)
class PracticeLessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'unit', 'order', 'created_at']
    list_filter = ['unit__course', 'created_at']
    search_fields = ['title']
    inlines = [PracticeChallengeInline]
    ordering = ['unit__course', 'unit__order', 'order']


@admin.register(PracticeChallenge)
class PracticeChallengeAdmin(admin.ModelAdmin):
    list_display = ['question', 'type', 'lesson', 'order', 'created_at']
    list_filter = ['type', 'lesson__unit__course', 'created_at']
    search_fields = ['question']
    inlines = [ChallengeOptionInline]
    ordering = ['lesson__unit__course', 'lesson__unit__order', 'lesson__order', 'order']


@admin.register(ChallengeOption)
class ChallengeOptionAdmin(admin.ModelAdmin):
    list_display = ['text', 'challenge', 'is_correct', 'order']
    list_filter = ['is_correct', 'challenge__type']
    search_fields = ['text']
    ordering = ['challenge__lesson__unit__course', 'challenge__order', 'order']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'active_course', 'hearts', 'points', 'updated_at']
    list_filter = ['active_course', 'hearts', 'updated_at']
    search_fields = ['user__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChallengeProgress)
class ChallengeProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'completed', 'completed_at']
    list_filter = ['completed', 'challenge__type', 'completed_at']
    search_fields = ['user__name', 'challenge__question']
    readonly_fields = ['completed_at', 'updated_at']
