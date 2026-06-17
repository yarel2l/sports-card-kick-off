from django.urls import path

from .consumers import NotificationConsumer

websocket_urlpatterns = [
    # Per-user real-time notifications (search status, price alerts).
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
