"""
Configuración ASGI (Clase 9): un mismo servidor (Daphne) atiende HTTP y WebSocket.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Primero se inicializa Django y recién después se importa el routing, que importa modelos
# (si se invierte el orden aparece AppRegistryNotReady, Clase 9)
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

import pedidos.routing  # noqa: E402
from pedidos.ws_auth import JWTAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter({
    # HTTP: la API REST de siempre
    "http": django_asgi_app,
    # WebSocket: primero la sesión, después el JWT de ?token=, y recién ahí el consumer
    "websocket": AuthMiddlewareStack(
        JWTAuthMiddleware(
            URLRouter(pedidos.routing.websocket_urlpatterns)
        )
    ),
})
