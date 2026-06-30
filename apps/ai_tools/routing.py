"""ai_tools/routing.py"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/chatbot/(?P<session_id>\d+)/$', consumers.ChatbotStreamConsumer.as_asgi()),
]
