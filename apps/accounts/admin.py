"""accounts/admin.py"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, StudentProfile, TeacherProfile, Notification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'level', 'is_active', 'date_joined']
    list_filter = ['role', 'level', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Informations plateforme'), {
            'fields': ('role', 'level', 'bio', 'avatar', 'phone',
                       'date_of_birth', 'preferred_language', 'is_email_verified')
        }),
        (_('Enseignant'), {
            'fields': ('specialization', 'years_experience'),
            'classes': ['collapse'],
        }),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_points', 'streak_days', 'last_activity']
    search_fields = ['user__username', 'user__email']


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'institution', 'ai_training_completed', 'total_students_taught']
    list_filter = ['ai_training_completed']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notif_type', 'is_read', 'created_at']
    list_filter = ['notif_type', 'is_read']
    search_fields = ['title', 'user__username']
