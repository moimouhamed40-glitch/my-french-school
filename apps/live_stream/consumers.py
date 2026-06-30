"""
live_stream/consumers.py

WebSocket consumers for:
- Live session chat
- Polls (create / vote / results)
- Whiteboard sync
- Participant presence (join/leave)
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class LiveSessionConsumer(AsyncWebsocketConsumer):
    """
    Main WebSocket consumer for a live session.
    Handles: chat, polls, whiteboard, presence.

    URL pattern: ws/live/<session_uid>/
    Groups:
        session_<uid>          – all participants
        session_<uid>_host     – host only
    """

    async def connect(self):
        self.session_uid = self.scope['url_route']['kwargs']['session_uid']
        self.room_group = f"session_{self.session_uid}"
        self.host_group = f"session_{self.session_uid}_host"
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        session = await self.get_session(self.session_uid)
        if not session:
            await self.close(code=4004)
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group, self.channel_name)

        # Join host group if applicable
        if self.user.pk == session.host_id:
            await self.channel_layer.group_add(self.host_group, self.channel_name)

        await self.accept()

        # Register participant
        await self.register_participant(session)

        # Broadcast join event
        await self.channel_layer.group_send(self.room_group, {
            'type': 'presence_event',
            'event': 'join',
            'user_id': self.user.pk,
            'username': self.user.username,
            'display_name': self.user.get_full_name() or self.user.username,
            'role': self.user.role,
        })

        # Send recent chat history to this user
        history = await self.get_chat_history(session)
        await self.send(text_data=json.dumps({
            'type': 'chat_history',
            'messages': history,
        }))

    async def disconnect(self, close_code):
        if not hasattr(self, 'room_group'):
            return

        # Mark participant as left
        await self.mark_participant_left(self.session_uid)

        # Broadcast leave event
        await self.channel_layer.group_send(self.room_group, {
            'type': 'presence_event',
            'event': 'leave',
            'user_id': self.user.pk,
            'username': self.user.username,
        })

        await self.channel_layer.group_discard(self.room_group, self.channel_name)
        await self.channel_layer.group_discard(self.host_group, self.channel_name)

    async def receive(self, text_data):
        """Route incoming messages by type."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON')
            return

        msg_type = data.get('type')

        handlers = {
            'chat_message': self.handle_chat_message,
            'poll_create': self.handle_poll_create,
            'poll_vote': self.handle_poll_vote,
            'poll_close': self.handle_poll_close,
            'whiteboard_update': self.handle_whiteboard_update,
            'whiteboard_save': self.handle_whiteboard_save,
            'raise_hand': self.handle_raise_hand,
            'session_end': self.handle_session_end,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(data)
        else:
            await self.send_error(f'Unknown message type: {msg_type}')

    # ── CHAT ──────────────────────────────────────────────────────────────────

    async def handle_chat_message(self, data):
        message = data.get('message', '').strip()
        if not message:
            return

        # Persist to DB
        saved = await self.save_chat_message(self.session_uid, message)

        # Broadcast to group
        await self.channel_layer.group_send(self.room_group, {
            'type': 'chat_broadcast',
            'message_id': saved['id'],
            'sender_id': self.user.pk,
            'username': self.user.username,
            'display_name': self.user.get_full_name() or self.user.username,
            'avatar': self.user.get_avatar_url(),
            'message': message,
            'sent_at': saved['sent_at'],
        })

    async def chat_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            **{k: v for k, v in event.items() if k != 'type'},
        }))

    # ── POLLS ─────────────────────────────────────────────────────────────────

    async def handle_poll_create(self, data):
        """Only the host can create polls."""
        session = await self.get_session(self.session_uid)
        if self.user.pk != session.host_id:
            await self.send_error('Only the host can create polls.')
            return

        poll = await self.create_poll(
            self.session_uid,
            question=data.get('question', ''),
            poll_type=data.get('poll_type', 'yes_no'),
            options=data.get('options', []),
        )

        await self.channel_layer.group_send(self.room_group, {
            'type': 'poll_broadcast',
            'action': 'new_poll',
            'poll_id': poll['id'],
            'question': poll['question'],
            'poll_type': poll['poll_type'],
            'options': poll['options'],
        })

    async def handle_poll_vote(self, data):
        poll_id = data.get('poll_id')
        choice = data.get('choice', '')
        if not poll_id or not choice:
            return

        success, results = await self.register_vote(poll_id, self.user.pk, choice)
        if not success:
            await self.send_error('Vote failed — poll may be closed or already voted.')
            return

        await self.channel_layer.group_send(self.room_group, {
            'type': 'poll_broadcast',
            'action': 'poll_update',
            'poll_id': poll_id,
            'results': results,
        })

    async def handle_poll_close(self, data):
        session = await self.get_session(self.session_uid)
        if self.user.pk != session.host_id:
            return
        poll_id = data.get('poll_id')
        results = await self.close_poll(poll_id)
        await self.channel_layer.group_send(self.room_group, {
            'type': 'poll_broadcast',
            'action': 'poll_closed',
            'poll_id': poll_id,
            'results': results,
        })

    async def poll_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'poll_event',
            **{k: v for k, v in event.items() if k != 'type'},
        }))

    # ── WHITEBOARD ────────────────────────────────────────────────────────────

    async def handle_whiteboard_update(self, data):
        """Relay whiteboard drawing ops to all participants in real-time."""
        await self.channel_layer.group_send(self.room_group, {
            'type': 'whiteboard_relay',
            'sender_id': self.user.pk,
            'op': data.get('op'),       # e.g. {tool, path, color, width}
        })

    async def handle_whiteboard_save(self, data):
        """Host saves a full snapshot of the whiteboard canvas."""
        session = await self.get_session(self.session_uid)
        if self.user.pk != session.host_id:
            return
        await self.save_whiteboard_snapshot(self.session_uid, data.get('snapshot', {}))

    async def whiteboard_relay(self, event):
        # Don't echo back to the sender
        if event['sender_id'] == self.user.pk:
            return
        await self.send(text_data=json.dumps({
            'type': 'whiteboard_op',
            'op': event['op'],
        }))

    # ── PRESENCE ──────────────────────────────────────────────────────────────

    async def handle_raise_hand(self, data):
        raised = data.get('raised', True)
        await self.channel_layer.group_send(self.room_group, {
            'type': 'presence_event',
            'event': 'raise_hand',
            'user_id': self.user.pk,
            'username': self.user.username,
            'raised': raised,
        })

    async def presence_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'presence',
            **{k: v for k, v in event.items() if k != 'type'},
        }))

    # ── SESSION CONTROL ───────────────────────────────────────────────────────

    async def handle_session_end(self, data):
        session = await self.get_session(self.session_uid)
        if self.user.pk != session.host_id:
            return
        await self.end_session(self.session_uid)
        await self.channel_layer.group_send(self.room_group, {
            'type': 'session_terminated',
            'message': 'La session a été terminée par l\'enseignant.',
        })

    async def session_terminated(self, event):
        await self.send(text_data=json.dumps({
            'type': 'session_end',
            'message': event['message'],
        }))
        await self.close()

    # ── HELPERS ───────────────────────────────────────────────────────────────

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
        }))

    # ── DATABASE HELPERS (sync_to_async) ──────────────────────────────────────

    @database_sync_to_async
    def get_session(self, uid):
        from .models import LiveSession
        try:
            return LiveSession.objects.get(uid=uid)
        except LiveSession.DoesNotExist:
            return None

    @database_sync_to_async
    def register_participant(self, session):
        from .models import SessionParticipant
        SessionParticipant.objects.update_or_create(
            session=session,
            user=self.user,
            defaults={'left_at': None},
        )

    @database_sync_to_async
    def mark_participant_left(self, uid):
        from .models import LiveSession, SessionParticipant
        try:
            session = LiveSession.objects.get(uid=uid)
            SessionParticipant.objects.filter(
                session=session, user=self.user
            ).update(left_at=timezone.now())
        except LiveSession.DoesNotExist:
            pass

    @database_sync_to_async
    def get_chat_history(self, session, limit=50):
        from .models import ChatMessage
        msgs = ChatMessage.objects.filter(session=session).order_by('-sent_at')[:limit]
        return [
            {
                'message_id': m.pk,
                'sender_id': m.sender_id,
                'username': m.sender.username,
                'display_name': m.sender.get_full_name() or m.sender.username,
                'message': m.message,
                'sent_at': m.sent_at.isoformat(),
            }
            for m in reversed(list(msgs))
        ]

    @database_sync_to_async
    def save_chat_message(self, uid, message):
        from .models import LiveSession, ChatMessage
        session = LiveSession.objects.get(uid=uid)
        msg = ChatMessage.objects.create(
            session=session,
            sender=self.user,
            message=message,
        )
        return {'id': msg.pk, 'sent_at': msg.sent_at.isoformat()}

    @database_sync_to_async
    def create_poll(self, uid, question, poll_type, options):
        from .models import LiveSession, Poll
        session = LiveSession.objects.get(uid=uid)
        poll = Poll.objects.create(
            session=session,
            question=question,
            poll_type=poll_type,
            options=options,
        )
        return {
            'id': poll.pk,
            'question': poll.question,
            'poll_type': poll.poll_type,
            'options': poll.options,
        }

    @database_sync_to_async
    def register_vote(self, poll_id, user_id, choice):
        from .models import Poll, PollVote
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            poll = Poll.objects.get(pk=poll_id, is_open=True)
            voter = User.objects.get(pk=user_id)
            PollVote.objects.create(poll=poll, voter=voter, choice=choice)
            return True, poll.get_results()
        except (Poll.DoesNotExist, Exception):
            return False, {}

    @database_sync_to_async
    def close_poll(self, poll_id):
        from .models import Poll
        try:
            poll = Poll.objects.get(pk=poll_id)
            poll.is_open = False
            poll.closed_at = timezone.now()
            poll.save()
            return poll.get_results()
        except Poll.DoesNotExist:
            return {}

    @database_sync_to_async
    def save_whiteboard_snapshot(self, uid, snapshot_data):
        from .models import LiveSession, WhiteboardSnapshot
        session = LiveSession.objects.get(uid=uid)
        WhiteboardSnapshot.objects.create(session=session, snapshot_data=snapshot_data)

    @database_sync_to_async
    def end_session(self, uid):
        from .models import LiveSession
        LiveSession.objects.filter(uid=uid).update(
            status=LiveSession.Status.ENDED,
            is_active=False,
            ended_at=timezone.now(),
        )
