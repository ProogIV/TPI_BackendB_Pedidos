"""
Capa de servicios (Clase 5): lógica de negocio y comunicación con los otros microservicios.

Las vistas no saben que existen Inventario o Pagos: solo llaman a PedidoService.crear_pedido().
"""

import logging
from decimal import Decimal

import requests
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


class InventarioClient:
    """Llamadas HTTP al servicio de Inventario (spec.md, sección 4.1)."""

    @staticmethod
    def descontar_stock(producto_id, cantidad):
        url = f"{settings.INVENTARIO_API_URL}/productos/{producto_id}/descontar"
        try:
            respuesta = requests.patch(url, json={"cantidad": cantidad}, timeout=settings.TIMEOUT_SERVICIOS)
        except requests.RequestException:
            # Inventario apagado o no respondió en 5 segundos (timeout)
            raise ServicioNoDisponible("El servicio de Inventario no está disponible.")

        if respuesta.status_code == 200:
            return respuesta.json()
        if respuesta.status_code == 404:
            raise ProductoNoEncontrado(_mensaje_de_error(respuesta, "El producto no existe o está inactivo."))
        if respuesta.status_code == 400:
            raise PedidoRechazado(_mensaje_de_error(respuesta, "Inventario rechazó el pedido."))
        raise ServicioNoDisponible("El servicio de Inventario respondió con un error inesperado.")

    @staticmethod
    def reponer_stock(producto_id, cantidad):
        """Compensación: devuelve el stock si el cobro falló. Devuelve True si se pudo."""
        url = f"{settings.INVENTARIO_API_URL}/productos/{producto_id}/reponer"
        try:
            respuesta = requests.patch(url, json={"cantidad": cantidad}, timeout=settings.TIMEOUT_SERVICIOS)
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

        # TP 3: acá se enviará la notificación por WebSocket (spec.md, sección 8)
        return pedido
