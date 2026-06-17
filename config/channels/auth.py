"""
JWT authentication middleware for Channels (WebSocket) connections.

Browsers cannot set Authorization headers on WebSocket handshakes, so the
access token is passed as a ``?token=`` query-string parameter. The middleware
validates it with SimpleJWT and puts the resolved user on the connection scope
(``AnonymousUser`` if missing/invalid). Consumers decide whether to accept.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user(token: str):
    from django.contrib.auth import get_user_model
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.settings import api_settings
    from rest_framework_simplejwt.tokens import AccessToken

    try:
        access = AccessToken(token)
    except TokenError:
        return AnonymousUser()

    User = get_user_model()
    try:
        user_id = access[api_settings.USER_ID_CLAIM]
        return User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        token = None
        query_string = scope.get('query_string', b'').decode()
        if query_string:
            token = (parse_qs(query_string).get('token') or [None])[0]
        scope['user'] = await _get_user(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
