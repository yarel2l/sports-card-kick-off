"""
WebSocket consumers.

``NotificationConsumer`` is a per-user channel: once authenticated, the
connection joins the group ``user_<account_id>`` and receives server-pushed
events (search status updates, triggered price alerts) in real time.
"""

import json

from channels.generic.websocket import AsyncWebsocketConsumer


def user_group_name(user_pk) -> str:
    return f"user_{user_pk}"


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not getattr(user, 'is_authenticated', False):
            # 4401 = application-level "unauthorized".
            await self.close(code=4401)
            return

        self.group_name = user_group_name(user.pk)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({'event': 'connected'}))

    async def disconnect(self, code):
        group = getattr(self, 'group_name', None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def notify(self, event):
        """Handler for messages with ``{'type': 'notify', ...}``."""
        await self.send(text_data=json.dumps({
            'event': event.get('event'),
            'data': event.get('data'),
        }))
