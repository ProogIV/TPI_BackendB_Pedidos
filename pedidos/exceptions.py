import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Manejador centralizado de errores (Clase 4), adaptado al formato uniforme del spec.md:

        {"error": true, "mensaje": "...", "detalles": {...}}

    - Errores con un único mensaje (404, 401, 403, 429...) → "mensaje" con ese texto.
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

    if isinstance(datos, dict) and set(datos.keys()) == {"detail"}:
        cuerpo = {"error": True, "mensaje": str(datos["detail"])}
    else:
        cuerpo = {
            "error": True,
            "mensaje": "Error de validación en los datos enviados",
            "detalles": datos,
        }

    response.data = cuerpo
    return response
