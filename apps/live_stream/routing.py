"""live_stream/routing.py - WebSocket URL routing"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/live/(?P<session_uid>[0-9a-f-]+)/$', consumers.LiveSessionConsumer.as_asgi()),
]
