"""
Autenticación del WebSocket con JWT (Clase 10).

El WebSocket del navegador no permite mandar el header Authorization, por eso el access token
viaja en la URL: ws://localhost:8000/ws/pedidos/?token=<access>
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token(token):
    User = get_user_model()
    try:
        # Misma validación que la API REST: firma (JWT_SIGNING_KEY) y vencimiento
        access = AccessToken(token)
        return User.objects.get(id=access["user_id"], is_active=True)
    except (TokenError, KeyError, ValueError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Lee ?token=<access> de la URL del WebSocket y completa scope["user"]."""

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = query.get("token", [None])[0]
        if token:
            scope["user"] = await get_user_from_token(token)
        return await super().__call__(scope, receive, send)
