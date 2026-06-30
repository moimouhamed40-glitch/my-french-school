"""courses/admin.py"""

from django.contrib import admin
from .models import (
    Category, Course, Lesson, Exercise, ExerciseSubmission,
    Enrollment, CourseProgress, LiteraryText, ForumThread, ForumReply,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ['title', 'lesson_type', 'order', 'video_url', 'duration_minutes']


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 0
    fields = ['title', 'exercise_type', 'points', 'order']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'teacher', 'status', 'is_published', 'enrolled_count', 'created_at']
    list_filter = ['level', 'status', 'is_published', 'is_free']
    search_fields = ['title', 'description', 'teacher__username']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LessonInline]

    def enrolled_count(self, obj):
        return obj.enrollments.count()
    enrolled_count.short_description = 'Élèves inscrits'


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'lesson_type', 'order', 'duration_minutes']
    list_filter = ['lesson_type']
    search_fields = ['title', 'course__title']
    inlines = [ExerciseInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ['title', 'exercise_type', 'course', 'points', 'ai_generated']
    list_filter = ['exercise_type', 'ai_generated']


@admin.register(ExerciseSubmission)
class ExerciseSubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'exercise', 'is_correct', 'score', 'submitted_at']
    list_filter = ['is_correct']
    search_fields = ['student__username']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'enrolled_at', 'is_completed', 'final_grade']
    list_filter = ['is_completed']


@admin.register(LiteraryText)
class LiteraryTextAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'level']
    list_filter = ['level']


@admin.register(ForumThread)
class ForumThreadAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'course', 'is_pinned', 'is_closed', 'created_at']
    list_filter = ['is_pinned', 'is_closed']
