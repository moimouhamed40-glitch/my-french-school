"""live_stream/admin.py"""

from django.contrib import admin
from .models import (
    LiveSession, SessionParticipant, SessionRecording,
    ChatMessage, Poll, PollVote, WhiteboardSnapshot,
)


class SessionParticipantInline(admin.TabularInline):
    model = SessionParticipant
    extra = 0
    readonly_fields = ['joined_at', 'left_at']


class PollInline(admin.TabularInline):
    model = Poll
    extra = 0
    fields = ['question', 'poll_type', 'is_open']


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'host', 'status', 'is_active', 'scheduled_at',
                    'started_at', 'participant_count']
    list_filter = ['status', 'is_active', 'enable_recording']
    search_fields = ['title', 'host__username']
    readonly_fields = ['uid', 'agora_channel', 'started_at', 'ended_at']
    inlines = [SessionParticipantInline, PollInline]

    def participant_count(self, obj):
        return obj.participants.count()


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ['question', 'session', 'poll_type', 'is_open', 'vote_count']
    list_filter = ['poll_type', 'is_open']

    def vote_count(self, obj):
        return obj.votes.count()


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'session', 'message_preview', 'sent_at']
    search_fields = ['sender__username', 'message']

    def message_preview(self, obj):
        return obj.message[:60]


@admin.register(SessionRecording)
class SessionRecordingAdmin(admin.ModelAdmin):
    list_display = ['session', 'duration_seconds', 'file_size_mb', 'created_at']
