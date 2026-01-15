"""
WebSocket URL routing for climbing sessions.

Defines WebSocket endpoints for real-time messaging in climbing sessions.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/sessions/(?P<session_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
]
