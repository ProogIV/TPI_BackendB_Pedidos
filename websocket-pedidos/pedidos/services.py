"""
Capa de servicios (Clase 5): lógica de negocio y comunicación con los otros microservicios.

Las vistas no saben que existen Inventario o Pagos: solo llaman a PedidoService.crear_pedido().
"""

import logging
from decimal import Decimal

import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from .exceptions import PedidoRechazado, ProductoNoEncontrado, ServicioNoDisponible
from .models import Pedido
from .repositories import PedidoRepository

logger = logging.getLogger(__name__)


def _mensaje_de_error(respuesta, por_defecto):
    """Toma el 'mensaje' del formato uniforme de error que devuelven los otros servicios."""
    try:
        return respuesta.json().get("mensaje", por_defecto)
    except ValueError:  # la respuesta no era JSON
        return por_defecto


def _headers_de_servicio():
    """Pedidos se identifica ante Inventario con la clave compartida (spec.md, sección 7)."""
    return {"X-Service-Token": settings.SERVICE_TOKEN}


class InventarioClient:
    """Llamadas HTTP al servicio de Inventario (spec.md, sección 4.1)."""

    @staticmethod
    def descontar_stock(producto_id, cantidad):
        url = f"{settings.INVENTARIO_API_URL}/productos/{producto_id}/descontar"
        try:
            respuesta = requests.patch(
                url, json={"cantidad": cantidad}, headers=_headers_de_servicio(), timeout=settings.TIMEOUT_SERVICIOS
            )
        except requests.RequestException:
            # Inventario apagado o no respondió en 5 segundos (timeout)
            raise ServicioNoDisponible("El servicio de Inventario no está disponible.")

        if respuesta.status_code == 200:
            return respuesta.json()
        if respuesta.status_code == 404:
            raise ProductoNoEncontrado(_mensaje_de_error(respuesta, "El producto no existe o está inactivo."))
        if respuesta.status_code == 403:
            # La clave de servicio no coincide: es un error de configuración, no del cliente
            logger.error("Inventario rechazó el X-Service-Token: revisar SERVICE_TOKEN en ambos .env")
            raise ServicioNoDisponible("No se pudo autorizar la operación con Inventario.")
        if respuesta.status_code == 400:
            raise PedidoRechazado(_mensaje_de_error(respuesta, "Inventario rechazó el pedido."))
        raise ServicioNoDisponible("El servicio de Inventario respondió con un error inesperado.")

    @staticmethod
    def reponer_stock(producto_id, cantidad):
        """Compensación: devuelve el stock si el cobro falló. Devuelve True si se pudo."""
        url = f"{settings.INVENTARIO_API_URL}/productos/{producto_id}/reponer"
        try:
            respuesta = requests.patch(
                url, json={"cantidad": cantidad}, headers=_headers_de_servicio(), timeout=settings.TIMEOUT_SERVICIOS
            )
        except requests.RequestException:
            return False
        return respuesta.status_code == 200


class PagosClient:
    """Llamadas HTTP al servicio de Pagos (spec.md, sección 4.3)."""

    @staticmethod
    def procesar_pago(order_id, monto):
        """Devuelve la respuesta de Pagos, o None si no respondió o respondió con error."""
        url = f"{settings.PAGOS_API_URL}/payments/process"
        try:
            respuesta = requests.post(
                url,
                json={"order_id": order_id, "monto": float(monto)},
                timeout=settings.TIMEOUT_SERVICIOS,
            )
        except requests.RequestException:
            return None
        if respuesta.status_code != 200:
            return None
        return respuesta.json()


class PedidoService:
    @staticmethod
    def crear_pedido(producto_id, cantidad, cliente=None):
        """
        Flujo de compra completo (spec.md, sección 5):

        1. Pide a Inventario que descuente el stock. Si no hay stock, NO se crea el pedido.
        2. Crea el pedido PENDIENTE con el precio que informó Inventario.
        3. Pide el cobro a Pagos.
        4. APROBADO → PAGADO. Rechazado o Pagos caído → FALLIDO y se repone el stock.
        """
        # 1. Descontar stock (si falla, la excepción corta el flujo y no se crea nada)
        producto = InventarioClient.descontar_stock(producto_id, cantidad)

        # 2. Crear el pedido. Si algo falla acá, el stock ya se descontó: hay que devolverlo.
        try:
            pedido = PedidoRepository.crear(
                cliente=cliente,
                producto_id=producto_id,
                cantidad=cantidad,
                precio_unitario=Decimal(str(producto["precio"])),
            )
        except Exception:
            InventarioClient.reponer_stock(producto_id, cantidad)
            raise

        # 3. Cobrar
        pago = PagosClient.procesar_pago(pedido.id, pedido.monto_total)

        # 4. Resultado
        if pago and pago.get("estado") == "APROBADO":
            PedidoRepository.actualizar_estado(pedido, Pedido.Estado.PAGADO, pago.get("transaccion_id"))
        else:
            PedidoRepository.actualizar_estado(pedido, Pedido.Estado.FALLIDO)
            if not InventarioClient.reponer_stock(producto_id, cantidad):
                logger.error(
                    "No se pudo reponer el stock del pedido %s (producto %s, cantidad %s). Corregir a mano.",
                    pedido.id, producto_id, cantidad,
                )

        # 5. Avisar por WebSocket: el pedido ya está guardado con su estado final (Clase 10)
        NotificacionService.pedido_actualizado(pedido)
        return pedido


class NotificacionService:
    """
    Publica eventos en tiempo real (Clase 10, patrón Productor → Broker → Consumidor).

    El servicio no sabe cuántas conexiones hay abiertas: solo publica en los grupos y el
    channel layer se lo reparte a cada WebSocket conectado (pedidos/consumers.py).
    """

    GRUPO_ADMIN = "pedidos_admin"

    @staticmethod
    def grupo_usuario(usuario_id):
        return f"pedidos_usuario_{usuario_id}"

    @staticmethod
    def pedido_actualizado(pedido):
        payload = {
            "tipo": "pedido_actualizado",
            "pedido": {
                "id": pedido.id,
                "estado": pedido.estado,
                "monto_total": str(pedido.monto_total),
                "producto_id": pedido.producto_id,
            },
        }
        # El dueño del pedido recibe el aviso; los ADMIN reciben todos (spec.md, sección 8)
        grupos = [NotificacionService.GRUPO_ADMIN]
        if pedido.cliente_id:
            grupos.append(NotificacionService.grupo_usuario(pedido.cliente_id))
        for grupo in grupos:
            NotificacionService._send(grupo, payload)

    @staticmethod
    def _send(grupo, payload):
        channel_layer = get_channel_layer()
        try:
            async_to_sync(channel_layer.group_send)(
                grupo,
                {
                    "type": "pedido_actualizado",  # coincide con el método del consumer
                    "payload": payload,
                },
            )
        except Exception:
            # Si Redis está caído, el pedido igual se guardó: solo queda registrado en el log
            logger.exception("No se pudo enviar la notificación en tiempo real")
