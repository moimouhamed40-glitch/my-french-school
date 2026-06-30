"""
ASGI config for my_french_school project.
Handles both HTTP and WebSocket connections.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_french_school.settings')

django_asgi_app = get_asgi_application()

from apps.live_stream.routing import websocket_urlpatterns as live_ws
from apps.ai_tools.routing import websocket_urlpatterns as ai_ws

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                live_ws + ai_ws
            )
        )
    ),
})
