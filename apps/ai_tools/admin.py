"""ai_tools/admin.py"""

from django.contrib import admin
from .models import (
    AITrainingVideo, AITemplate, AIExerciseGeneration,
    GrammarCorrectionLog, ChatbotSession, TeacherProject,
)


@admin.register(AITrainingVideo)
class AITrainingVideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'difficulty', 'duration_minutes', 'order']
    list_filter = ['category', 'difficulty']
    ordering = ['category', 'order']


@admin.register(AITemplate)
class AITemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'template_type', 'level', 'usage_count', 'created_at']
    list_filter = ['template_type', 'level']
    search_fields = ['title']


@admin.register(AIExerciseGeneration)
class AIExerciseGenerationAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'grammar_rule', 'level', 'exercises_created', 'tokens_used', 'generated_at']
    list_filter = ['level', 'exercise_type']
    search_fields = ['teacher__username', 'grammar_rule']


@admin.register(GrammarCorrectionLog)
class GrammarCorrectionLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'error_count', 'created_at']
    search_fields = ['user__username']


@admin.register(ChatbotSession)
class ChatbotSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'total_messages', 'tokens_used', 'created_at']
    search_fields = ['user__username', 'title']


@admin.register(TeacherProject)
class TeacherProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'teacher', 'is_featured', 'likes', 'created_at']
    list_filter = ['is_featured']
    search_fields = ['title', 'teacher__username']
