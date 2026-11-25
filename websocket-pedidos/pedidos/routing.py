from django.urls import re_path

from . import consumers

# Por convención, las URLs de WebSocket empiezan con ws/ (Clase 9)
websocket_urlpatterns = [
    re_path(r"ws/pedidos/$", consumers.PedidoConsumer.as_asgi()),
]
