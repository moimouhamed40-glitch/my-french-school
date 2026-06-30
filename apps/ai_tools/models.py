"""
ai_tools/models.py

AI tool logs, teacher training content, AI templates, chatbot history.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AITrainingVideo(models.Model):
    """Training videos for teachers on how to use AI tools."""

    class ToolCategory(models.TextChoices):
        CHATGPT = 'chatgpt', 'ChatGPT'
        IMAGE_GEN = 'image_gen', _('Génération d\'images (DALL·E / Midjourney)')
        TTS = 'tts', _('Texte vers parole (TTS)')
        CONTENT = 'content', _('Création de contenu')
        ASSESSMENT = 'assessment', _('Évaluation & Quiz')
        OTHER = 'other', _('Autre')

    title = models.CharField(max_length=300)
    category = models.CharField(max_length=30, choices=ToolCategory.choices)
    description = models.TextField(blank=True)
    video_url = models.URLField()
    thumbnail = models.ImageField(upload_to='ai_training_thumbs/', null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    difficulty = models.CharField(
        max_length=20,
        choices=[('beginner', _('Débutant')), ('intermediate', _('Intermédiaire')), ('advanced', _('Avancé'))],
        default='beginner',
    )
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = _('Vidéo de formation IA')

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class AITemplate(models.Model):
    """Ready-made AI prompt templates for teachers."""

    class TemplateType(models.TextChoices):
        EXERCISE = 'exercise', _('Générateur d\'exercices')
        LESSON_PLAN = 'lesson_plan', _('Plan de cours')
        QUIZ = 'quiz', _('Quiz')
        FEEDBACK = 'feedback', _('Feedback élève')
        STORY = 'story', _('Histoire / Dialogue')
        VOCABULARY = 'vocabulary', _('Vocabulaire')

    title = models.CharField(max_length=300)
    template_type = models.CharField(max_length=30, choices=TemplateType.choices)
    level = models.CharField(
        max_length=5,
        choices=[('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1'), ('all', _('Tous niveaux'))],
        default='all',
    )
    prompt_template = models.TextField(help_text='Use {variable} placeholders')
    example_output = models.TextField(blank=True)
    variables = models.JSONField(default=list, help_text='List of variable names in the template')
    usage_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Modèle IA')
        verbose_name_plural = _('Modèles IA')

    def __str__(self):
        return f"[{self.get_template_type_display()}] {self.title}"


class AIExerciseGeneration(models.Model):
    """Log of AI-generated exercise batches."""

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_generations',
    )
    grammar_rule = models.CharField(max_length=300, verbose_name=_('Règle grammaticale'))
    level = models.CharField(max_length=5, choices=[('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1')])
    exercise_type = models.CharField(max_length=30)
    prompt_used = models.TextField()
    raw_response = models.TextField()
    exercises_created = models.PositiveSmallIntegerField(default=0)
    linked_course = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    tokens_used = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-generated_at']
        verbose_name = _('Génération d\'exercices IA')

    def __str__(self):
        return f"{self.teacher.username}: {self.grammar_rule} ({self.exercises_created} ex.)"


class GrammarCorrectionLog(models.Model):
    """Log of grammar corrections (spaCy)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    original_text = models.TextField()
    corrected_text = models.TextField()
    errors_found = models.JSONField(default=list)
    error_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Correction grammaticale')

    def __str__(self):
        return f"{self.user.username} – {self.error_count} erreurs"


class ChatbotSession(models.Model):
    """An AI chatbot conversation session for a student."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chatbot_sessions')
    title = models.CharField(max_length=200, blank=True, default='Nouvelle conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_messages = models.PositiveSmallIntegerField(default=0)
    tokens_used = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Session chatbot')

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class ChatbotMessage(models.Model):
    """A single message in a chatbot session."""

    class Role(models.TextChoices):
        USER = 'user', _('Utilisateur')
        ASSISTANT = 'assistant', _('Assistant')
        SYSTEM = 'system', _('Système')

    session = models.ForeignKey(ChatbotSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    tokens = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = _('Message chatbot')

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"


class TeacherProject(models.Model):
    """Teacher AI projects shown in the project gallery."""

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    description = models.TextField()
    thumbnail = models.ImageField(upload_to='project_gallery/', null=True, blank=True)
    project_url = models.URLField(blank=True)
    tools_used = models.JSONField(default=list)
    is_featured = models.BooleanField(default=False)
    likes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']
        verbose_name = _('Projet enseignant')

    def __str__(self):
        return f"{self.teacher.username}: {self.title}"
