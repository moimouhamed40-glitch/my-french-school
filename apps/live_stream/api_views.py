"""live_stream/api_views.py"""

from rest_framework import generics, permissions, serializers
from .models import LiveSession, ChatMessage, Poll


class SessionSerializer(serializers.ModelSerializer):
    host_name = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()

    class Meta:
        model = LiveSession
        fields = ['uid', 'title', 'status', 'host_name', 'participant_count',
                  'scheduled_at', 'started_at', 'agora_channel']

    def get_host_name(self, obj):
        return obj.host.get_full_name() or obj.host.username

    def get_participant_count(self, obj):
        return obj.participant_count


class ChatSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'sender_name', 'message', 'sent_at']

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username


class PollSerializer(serializers.ModelSerializer):
    results = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ['id', 'question', 'poll_type', 'options', 'is_open', 'results', 'created_at']

    def get_results(self, obj):
        return obj.get_results()


class SessionListAPIView(generics.ListAPIView):
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LiveSession.objects.filter(
            status__in=[LiveSession.Status.SCHEDULED, LiveSession.Status.LIVE]
        ).order_by('scheduled_at')


class SessionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = LiveSession.objects.all()
    lookup_field = 'uid'


class ChatHistoryAPIView(generics.ListAPIView):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatMessage.objects.filter(
            session__uid=self.kwargs['uid']
        ).order_by('sent_at')


class PollListAPIView(generics.ListAPIView):
    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Poll.objects.filter(session__uid=self.kwargs['uid']).order_by('-created_at')
