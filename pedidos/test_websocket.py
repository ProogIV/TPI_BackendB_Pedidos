"""
Tests del WebSocket de notificaciones (TP 3, spec.md sección 8).

Usan WebsocketCommunicator, el cliente de prueba de Channels, y el channel layer en memoria
(sin REDIS_URL no hace falta Redis). Son TransactionTestCase porque el consumer consulta la
base desde otro hilo (database_sync_to_async) y tiene que ver los datos ya confirmados.
"""

from decimal import Decimal

from asgiref.sync import sync_to_async
from channels.layers import channel_layers
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application

from .models import Pedido
from .services import NotificacionService


def url(token=None):
    return f"/ws/pedidos/?token={token}" if token else "/ws/pedidos/"


class WebSocketPedidosTests(TransactionTestCase):
    def setUp(self):
        # Un channel layer nuevo por test: cada test async corre en su propio bucle de eventos
        channel_layers.backends.clear()
        self.cliente = User.objects.create_user("ana", password="Clave12345!")
        self.otro = User.objects.create_user("beto", password="Clave12345!")
        self.admin = User.objects.create_user("jefa", password="Clave12345!", is_staff=True)
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            producto_id="665f1c2a9b1e8a0012345678",
            cantidad=2,
            precio_unitario=Decimal("185000.00"),
            estado=Pedido.Estado.PAGADO,
        )

    def token(self, usuario):
        return str(AccessToken.for_user(usuario))

    async def conectar(self, usuario):
        comunicador = WebsocketCommunicator(application, url(self.token(usuario)))
        conectado, _ = await comunicador.connect()
        self.assertTrue(conectado)
        return comunicador

    async def test_sin_token_se_rechaza_la_conexion(self):
        comunicador = WebsocketCommunicator(application, url())
        conectado, _ = await comunicador.connect()
        self.assertFalse(conectado)

    async def test_token_invalido_se_rechaza_la_conexion(self):
        comunicador = WebsocketCommunicator(application, url("esto-no-es-un-jwt"))
        conectado, _ = await comunicador.connect()
        self.assertFalse(conectado)

    async def test_el_cliente_recibe_el_aviso_de_su_pedido(self):
        comunicador = await self.conectar(self.cliente)

        await sync_to_async(NotificacionService.pedido_actualizado)(self.pedido)

        mensaje = await comunicador.receive_json_from(timeout=2)
        self.assertEqual(mensaje["tipo"], "pedido_actualizado")
        self.assertEqual(mensaje["pedido"]["id"], self.pedido.id)
        self.assertEqual(mensaje["pedido"]["estado"], "PAGADO")
        self.assertEqual(mensaje["pedido"]["monto_total"], "370000.00")
        await comunicador.disconnect()

    async def test_otro_cliente_no_recibe_pedidos_ajenos(self):
        comunicador = await self.conectar(self.otro)

        await sync_to_async(NotificacionService.pedido_actualizado)(self.pedido)

        self.assertTrue(await comunicador.receive_nothing(timeout=0.5))
        await comunicador.disconnect()

    async def test_el_admin_recibe_los_pedidos_de_todos(self):
        comunicador = await self.conectar(self.admin)

        await sync_to_async(NotificacionService.pedido_actualizado)(self.pedido)

        mensaje = await comunicador.receive_json_from(timeout=2)
        self.assertEqual(mensaje["pedido"]["id"], self.pedido.id)
        await comunicador.disconnect()
