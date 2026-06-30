"""
ai_tools/consumers.py

WebSocket consumer for streaming chatbot responses (token by token).
URL: ws/chatbot/<session_id>/
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings


class ChatbotStreamConsumer(AsyncWebsocketConsumer):
    """
    Streams OpenAI responses token-by-token to the browser.
    Provides a more responsive UX than waiting for the full response.
    """

    async def connect(self):
        self.user = self.scope['user']
        self.session_id = self.scope['url_route']['kwargs']['session_id']

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        """Receive a message and stream back the AI response."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        user_message = data.get('message', '').strip()
        if not user_message:
            return

        session = await self.get_session(self.session_id)
        if not session:
            await self.send(json.dumps({'type': 'error', 'message': 'Session not found'}))
            return

        # Send "typing" indicator
        await self.send(json.dumps({'type': 'typing', 'status': True}))

        # Save user message
        await self.save_message(session, 'user', user_message)

        # Stream response from OpenAI
        full_response = ''
        total_tokens = 0

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            history = await self.get_history(session)
            user_level = await self.get_user_level()

            stream = await client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            f"Tu es un assistant pédagogique FLE bienveillant. "
                            f"Niveau élève : {user_level}. "
                            "Réponds toujours en français sauf si la question est en arabe."
                        )
                    },
                    *history[-8:],
                    {'role': 'user', 'content': user_message},
                ],
                stream=True,
                max_tokens=800,
                temperature=0.6,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response += delta.content
                    await self.send(json.dumps({
                        'type': 'stream_chunk',
                        'chunk': delta.content,
                    }))

        except ImportError:
            full_response = "OpenAI non configuré. Vérifiez votre clé API."
        except Exception as e:
            full_response = f"Erreur : {str(e)}"

        # Stream done
        await self.send(json.dumps({
            'type': 'stream_done',
            'full_response': full_response,
        }))

        # Save assistant message
        if full_response:
            await self.save_message(session, 'assistant', full_response)
            await self.update_session(session, full_response)

    # ── DB HELPERS ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def get_session(self, session_id):
        from apps.ai_tools.models import ChatbotSession
        try:
            return ChatbotSession.objects.get(pk=session_id, user=self.user)
        except ChatbotSession.DoesNotExist:
            return None

    @database_sync_to_async
    def get_history(self, session):
        from apps.ai_tools.models import ChatbotMessage
        return [
            {'role': m.role, 'content': m.content}
            for m in ChatbotMessage.objects.filter(
                session=session
            ).exclude(role='system').order_by('created_at')[-10:]
        ]

    @database_sync_to_async
    def get_user_level(self):
        return getattr(self.user, 'level', 'A1') or 'A1'

    @database_sync_to_async
    def save_message(self, session, role, content):
        from apps.ai_tools.models import ChatbotMessage
        ChatbotMessage.objects.create(session=session, role=role, content=content)

    @database_sync_to_async
    def update_session(self, session, response):
        session.total_messages += 2
        session.save(update_fields=['total_messages', 'updated_at'])
