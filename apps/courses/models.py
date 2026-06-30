"""
courses/models.py

Course, lesson, exercise, submission, forum, and literary text models.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Nom'))
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Bootstrap icon class')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = _('Catégorie')
        verbose_name_plural = _('Catégories')

    def __str__(self):
        return self.name


class Course(models.Model):
    """A complete course with multiple lessons."""

    class Level(models.TextChoices):
        A1 = 'A1', 'A1 - Débutant'
        A2 = 'A2', 'A2 - Élémentaire'
        B1 = 'B1', 'B1 - Intermédiaire'

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        PUBLISHED = 'published', _('Publié')
        ARCHIVED = 'archived', _('Archivé')

    title = models.CharField(max_length=300, verbose_name=_('Titre'))
    slug = models.SlugField(unique=True)
    description = models.TextField(verbose_name=_('Description'))
    thumbnail = models.ImageField(upload_to='course_thumbnails/', null=True, blank=True)
    level = models.CharField(max_length=5, choices=Level.choices, default=Level.A1)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses_taught',
        limit_choices_to={'role': 'teacher'},
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_published = models.BooleanField(default=False)
    is_free = models.BooleanField(default=True)
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Cours')
        verbose_name_plural = _('Cours')

    def __str__(self):
        return f"[{self.level}] {self.title}"

    def get_absolute_url(self):
        return reverse('courses:detail', kwargs={'slug': self.slug})

    @property
    def total_lessons(self):
        return self.lessons.count()

    @property
    def enrolled_count(self):
        return self.enrollments.count()


class Lesson(models.Model):
    """A single lesson (video) inside a course."""

    class LessonType(models.TextChoices):
        VIDEO = 'video', _('Vidéo')
        TEXT = 'text', _('Texte')
        EXERCISE = 'exercise', _('Exercice')
        QUIZ = 'quiz', _('Quiz')

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=300)
    lesson_type = models.CharField(max_length=20, choices=LessonType.choices, default=LessonType.VIDEO)
    order = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True)
    video_url = models.URLField(blank=True, help_text='YouTube, Vimeo, or direct URL')
    video_file = models.FileField(upload_to='course_materials/videos/', blank=True, null=True)
    content = models.TextField(blank=True, help_text='Rich text content for text lessons')
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    is_free_preview = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Leçon')

    def __str__(self):
        return f"{self.course.title} — {self.order}. {self.title}"


class Exercise(models.Model):
    """An exercise attached to a lesson."""

    class ExerciseType(models.TextChoices):
        MCQ = 'mcq', _('QCM')
        FILL_BLANK = 'fill_blank', _('Compléter les trous')
        ORDER_SENTENCE = 'order_sentence', _('Ordonner la phrase')
        FREE_TEXT = 'free_text', _('Texte libre')

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='exercises', null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exercises')
    title = models.CharField(max_length=300)
    exercise_type = models.CharField(max_length=20, choices=ExerciseType.choices)
    question = models.TextField()
    # For MCQ: JSON list of choices. For fill_blank: text with [___] placeholders.
    # For order_sentence: JSON list of shuffled words.
    content_data = models.JSONField(default=dict, blank=True)
    correct_answer = models.JSONField(default=dict, help_text='Correct answer data')
    explanation = models.TextField(blank=True, help_text='Explanation shown after answering')
    points = models.PositiveSmallIntegerField(default=10)
    order = models.PositiveSmallIntegerField(default=0)
    ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Exercice')

    def __str__(self):
        return f"[{self.get_exercise_type_display()}] {self.title}"


class ExerciseSubmission(models.Model):
    """A student's answer to an exercise."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='submissions')
    answer_data = models.JSONField(default=dict)
    is_correct = models.BooleanField(default=False)
    score = models.PositiveSmallIntegerField(default=0)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    attempt_number = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = _('Soumission')

    def __str__(self):
        return f"{self.student.username} → {self.exercise.title} ({'✓' if self.is_correct else '✗'})"


class Enrollment(models.Model):
    """Student enrollment in a course."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    final_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ['student', 'course']
        verbose_name = _('Inscription')

    def __str__(self):
        return f"{self.student.username} ↔ {self.course.title}"


class CourseProgress(models.Model):
    """Track which lessons a student has completed."""

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)
    watch_time_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['student', 'lesson']
        verbose_name = _('Progression')

    def __str__(self):
        return f"{self.student.username} ✓ {self.lesson.title}"


class LiteraryText(models.Model):
    """French literary texts with Arabic translation of difficult words."""

    title = models.CharField(max_length=300, verbose_name=_('Titre'))
    author = models.CharField(max_length=200, blank=True, verbose_name=_('Auteur'))
    level = models.CharField(max_length=5, choices=Course.Level.choices, default='A2')
    body_text = models.TextField(verbose_name=_('Texte'))
    # JSON: {"word": "traduction_arabe", ...}
    word_translations = models.JSONField(default=dict, verbose_name=_('Traductions'))
    audio_url = models.URLField(blank=True, verbose_name=_('Audio'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Texte littéraire')
        verbose_name_plural = _('Textes littéraires')

    def __str__(self):
        return self.title


class ForumThread(models.Model):
    """Discussion forum thread."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='forum_threads', null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=400)
    body = models.TextField()
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = _('Discussion')

    def __str__(self):
        return self.title


class ForumReply(models.Model):
    """A reply inside a forum thread."""

    thread = models.ForeignKey(ForumThread, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    is_answer = models.BooleanField(default=False, help_text='Marked as the accepted answer')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = _('Réponse')

    def __str__(self):
        return f"Réponse de {self.author.username} dans '{self.thread.title}'"
