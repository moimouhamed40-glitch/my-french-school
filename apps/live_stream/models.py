"""
live_stream/models.py

Live virtual classroom sessions, participants, recordings, polls, whiteboard, and chat.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class LiveSession(models.Model):
    """A teacher-hosted live virtual classroom."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', _('Planifiée')
        LIVE = 'live', _('En cours')
        ENDED = 'ended', _('Terminée')
        CANCELLED = 'cancelled', _('Annulée')

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=300, verbose_name=_('Titre'))
    description = models.TextField(blank=True)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hosted_sessions',
        limit_choices_to={'role': 'teacher'},
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='live_sessions',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    is_active = models.BooleanField(default=False)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    max_participants = models.PositiveSmallIntegerField(default=50)

    # Agora / WebRTC
    agora_channel = models.CharField(max_length=200, blank=True)
    agora_token = models.TextField(blank=True)

    # Features
    enable_chat = models.BooleanField(default=True)
    enable_whiteboard = models.BooleanField(default=True)
    enable_screen_share = models.BooleanField(default=True)
    enable_recording = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_at', '-created_at']
        verbose_name = _('Session live')
        verbose_name_plural = _('Sessions live')

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"

    def get_join_url(self):
        from django.urls import reverse
        return reverse('live_stream:join', kwargs={'uid': self.uid})

    @property
    def participant_count(self):
        return self.participants.filter(left_at__isnull=True).count()

    def save(self, *args, **kwargs):
        # Auto-set agora channel name
        if not self.agora_channel:
            self.agora_channel = f"session_{self.uid.hex[:16]}"
        super().save(*args, **kwargs)


class SessionParticipant(models.Model):
    """Tracks who joined a live session and when."""

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    is_video_on = models.BooleanField(default=True)

    class Meta:
        unique_together = ['session', 'user']
        verbose_name = _('Participant')

    def __str__(self):
        return f"{self.user.username} → {self.session.title}"


class SessionRecording(models.Model):
    """Saved recording of a live session."""

    session = models.OneToOneField(
        LiveSession,
        on_delete=models.CASCADE,
        related_name='recording',
    )
    file = models.FileField(upload_to='stream_recordings/')
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    file_size_mb = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Enregistrement')

    def __str__(self):
        return f"Enregistrement: {self.session.title}"


class ChatMessage(models.Model):
    """A chat message inside a live session (persisted)."""

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_pinned = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sent_at']
        verbose_name = _('Message chat')

    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"


class Poll(models.Model):
    """An instant poll (Yes/No or multiple choice) in a live session."""

    class PollType(models.TextChoices):
        YES_NO = 'yes_no', _('Oui / Non')
        MULTIPLE = 'multiple', _('Choix multiple')

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='polls')
    question = models.CharField(max_length=500)
    poll_type = models.CharField(max_length=20, choices=PollType.choices, default=PollType.YES_NO)
    options = models.JSONField(default=list, help_text='List of option strings for multiple choice')
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Sondage')

    def __str__(self):
        return f"Sondage: {self.question[:60]}"

    def get_results(self):
        votes = self.votes.all()
        if self.poll_type == self.PollType.YES_NO:
            return {
                'yes': votes.filter(choice='yes').count(),
                'no': votes.filter(choice='no').count(),
                'total': votes.count(),
            }
        else:
            results = {}
            for opt in self.options:
                results[opt] = votes.filter(choice=opt).count()
            results['total'] = votes.count()
            return results


class PollVote(models.Model):
    """A user's vote in a poll."""

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    choice = models.CharField(max_length=200)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['poll', 'voter']
        verbose_name = _('Vote')

    def __str__(self):
        return f"{self.voter.username} → {self.choice}"


class WhiteboardSnapshot(models.Model):
    """Periodic snapshots of whiteboard state."""

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='whiteboard_snapshots')
    snapshot_data = models.JSONField(default=dict, help_text='Canvas JSON state')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-saved_at']
        verbose_name = _('Tableau blanc')

    def __str__(self):
        return f"Tableau: {self.session.title} @ {self.saved_at}"
