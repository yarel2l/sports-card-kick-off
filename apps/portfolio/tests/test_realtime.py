"""
WebSocket / realtime notification tests.

Uses an in-memory channel layer and drives the consumer with Channels'
WebsocketCommunicator. TransactionTestCase is required so the user created in
the test is committed and visible to the JWT auth middleware, which runs the
lookup on a separate thread.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from django.urls import path
from rest_framework_simplejwt.tokens import AccessToken

from config.channels.auth import JWTAuthMiddleware
from config.channels.consumers import NotificationConsumer, user_group_name

User = get_user_model()

application = JWTAuthMiddleware(
    URLRouter([path('ws/notifications/', NotificationConsumer.as_asgi())])
)

_INMEMORY = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


@override_settings(CHANNEL_LAYERS=_INMEMORY)
class NotificationConsumerTests(TransactionTestCase):
    def test_authenticated_connects_and_receives_push(self):
        user = User.objects.create_user(
            email='ws@example.com', username='ws', password='pass12345'
        )
        token = str(AccessToken.for_user(user))

        async def scenario():
            comm = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
            connected, _ = await comm.connect()
            self.assertTrue(connected)

            hello = await comm.receive_json_from(timeout=2)
            self.assertEqual(hello['event'], 'connected')

            # Server-side push to the user's group is delivered to the socket.
            layer = get_channel_layer()
            await layer.group_send(
                user_group_name(user.pk),
                {'type': 'notify', 'event': 'alert.triggered', 'data': {'card': 'x'}},
            )
            msg = await comm.receive_json_from(timeout=2)
            self.assertEqual(msg['event'], 'alert.triggered')
            self.assertEqual(msg['data'], {'card': 'x'})

            await comm.disconnect()

        async_to_sync(scenario)()

    def test_unauthenticated_is_rejected(self):
        async def scenario():
            comm = WebsocketCommunicator(application, "/ws/notifications/")
            connected, _ = await comm.connect()
            self.assertFalse(connected)
            await comm.disconnect()

        async_to_sync(scenario)()

    def test_invalid_token_is_rejected(self):
        async def scenario():
            comm = WebsocketCommunicator(
                application, "/ws/notifications/?token=not-a-real-token"
            )
            connected, _ = await comm.connect()
            self.assertFalse(connected)
            await comm.disconnect()

        async_to_sync(scenario)()


@override_settings(CHANNEL_LAYERS=_INMEMORY)
class NotifyHelperTests(TransactionTestCase):
    def test_notify_user_sends_to_group(self):
        from config.channels import notify

        async def scenario():
            layer = get_channel_layer()
            await layer.group_add('user_abc', 'test-channel')
            # notify_user is sync; run it off the event loop.
            from asgiref.sync import sync_to_async
            await sync_to_async(notify.notify_user)('abc', 'ping', {'n': 1})
            message = await layer.receive('test-channel')
            self.assertEqual(message['type'], 'notify')
            self.assertEqual(message['event'], 'ping')
            self.assertEqual(message['data'], {'n': 1})

        async_to_sync(scenario)()
