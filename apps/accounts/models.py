"""
accounts/models.py

Custom User model with role-based access control.
Roles: admin, teacher, student, guest
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Extended user model with educational platform roles."""

    class Role(models.TextChoices):
        ADMIN = 'admin', _('Administrateur')
        TEACHER = 'teacher', _('Enseignant')
        STUDENT = 'student', _('Élève')
        GUEST = 'guest', _('Visiteur')

    class Level(models.TextChoices):
        A1 = 'A1', 'A1 - Débutant'
        A2 = 'A2', 'A2 - Élémentaire'
        B1 = 'B1', 'B1 - Intermédiaire'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name=_('Rôle'),
    )
    bio = models.TextField(blank=True, verbose_name=_('Biographie'))
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name=_('Avatar'),
    )
    level = models.CharField(
        max_length=5,
        choices=Level.choices,
        default=Level.A1,
        blank=True,
        verbose_name=_('Niveau'),
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Téléphone'))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('Date de naissance'))
    preferred_language = models.CharField(
        max_length=5,
        choices=[('fr', 'Français'), ('ar', 'العربية')],
        default='fr',
        verbose_name=_('Langue préférée'),
    )
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Teacher-specific fields
    specialization = models.CharField(max_length=200, blank=True, verbose_name=_('Spécialisation'))
    years_experience = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return '/static/images/default-avatar.png'


class StudentProfile(models.Model):
    """Extended profile for students with progress tracking."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
    )
    total_points = models.PositiveIntegerField(default=0)
    completed_courses = models.ManyToManyField(
        'courses.Course',
        blank=True,
        related_name='completed_by',
    )
    streak_days = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name=_('Notes personnelles'))

    class Meta:
        verbose_name = _('Profil élève')

    def __str__(self):
        return f"Profil de {self.user.username}"


class TeacherProfile(models.Model):
    """Extended profile for teachers."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
    )
    certification = models.CharField(max_length=300, blank=True)
    institution = models.CharField(max_length=300, blank=True)
    ai_training_completed = models.BooleanField(default=False)
    total_students_taught = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _('Profil enseignant')

    def __str__(self):
        return f"Profil enseignant: {self.user.username}"


class Notification(models.Model):
    """Platform notifications for users."""

    class NotifType(models.TextChoices):
        INFO = 'info', _('Information')
        SUCCESS = 'success', _('Succès')
        WARNING = 'warning', _('Avertissement')
        COURSE = 'course', _('Cours')
        LIVE = 'live', _('Session Live')
        GRADE = 'grade', _('Note')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notif_type = models.CharField(max_length=20, choices=NotifType.choices, default=NotifType.INFO)
    is_read = models.BooleanField(default=False)
    link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Notification')

    def __str__(self):
        return f"{self.title} → {self.user.username}"
