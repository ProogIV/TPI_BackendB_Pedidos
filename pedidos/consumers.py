import json

from channels.generic.websocket import AsyncWebsocketConsumer

from .services import NotificacionService


class PedidoConsumer(AsyncWebsocketConsumer):
    """
    ws/pedidos/?token=<access> (spec.md, sección 8)

    - CLIENTE: se une a pedidos_usuario_<id> y recibe solo los avisos de SUS pedidos.
    - ADMIN: se une además a pedidos_admin y recibe los de todos.

    Es solo de salida: el servidor avisa y el cliente escucha. Para comprar se sigue usando
    POST /api/orders/, que aplica todas las validaciones.
    """

    async def connect(self):
        self.grupos = []
        usuario = self.scope.get("user")

        # Mismas reglas que la API REST: sin token válido no hay conexión (Clase 10)
        if usuario is None or not usuario.is_authenticated:
            await self.close()
            return

        self.grupos.append(NotificacionService.grupo_usuario(usuario.id))
        if usuario.is_staff:
            self.grupos.append(NotificacionService.GRUPO_ADMIN)

        for grupo in self.grupos:
            await self.channel_layer.group_add(grupo, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Si la conexión fue rechazada, self.grupos está vacío y no hay nada que limpiar
        for grupo in self.grupos:
            await self.channel_layer.group_discard(grupo, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # El cliente no tiene nada que mandar por este canal: se ignoran sus mensajes
        pass

    async def pedido_actualizado(self, event):
        # Channels llama a este método por cada mensaje con "type": "pedido_actualizado"
        await self.send(text_data=json.dumps(event["payload"]))
