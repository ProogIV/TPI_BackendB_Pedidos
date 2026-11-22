import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# --- Errores del flujo de compra (spec.md, sección 5) ---
# Son excepciones de DRF: el manejador de abajo las convierte al formato uniforme.

class PedidoRechazado(APIException):
    """Inventario rechazó el descuento (por ejemplo, stock insuficiente)."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "El pedido fue rechazado por el servicio de Inventario."
    default_code = "pedido_rechazado"


class ProductoNoEncontrado(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "El producto no existe o está inactivo."
    default_code = "producto_no_encontrado"


class ServicioNoDisponible(APIException):
    """Un servicio del que dependemos no respondió a tiempo o respondió algo inesperado."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Un servicio necesario no está disponible. Intente más tarde."
    default_code = "servicio_no_disponible"


def custom_exception_handler(exc, context):
    """
    Manejador centralizado de errores (Clase 4), adaptado al formato uniforme del spec.md:

        {"error": true, "mensaje": "...", "detalles": {...}}

    - Errores con un único mensaje (404, 401, 403, 429, 503...) → "mensaje" con ese texto.
    - Errores de validación por campo (400 de un serializer) → mensaje general + "detalles".
    - Excepciones que DRF no conoce (un bug) → 500 sin exponer detalles internos.
    """
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Error no controlado en %s", context.get("view"))
        return Response(
            {"error": True, "mensaje": "Error interno del servidor"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    datos = response.data

    if isinstance(datos, dict) and "detail" in datos:
        # Errores con un mensaje principal. simplejwt agrega "code" y "messages" al "detail"
        # cuando el token es inválido: alcanza con el "detail" para el formato uniforme.
        cuerpo = {"error": True, "mensaje": str(datos["detail"])}
    else:
        cuerpo = {
            "error": True,
            "mensaje": "Error de validación en los datos enviados",
            "detalles": datos,
        }

    response.data = cuerpo
    return response
