from django.conf import settings
from rest_framework.permissions import BasePermission


def es_servicio_interno(request):
    """True si la petición trae el X-Service-Token correcto (spec.md, sección 7)."""
    clave = settings.SERVICE_TOKEN
    return bool(clave) and request.headers.get("X-Service-Token") == clave


class EsServicioInterno(BasePermission):
    """Permite que Inventario consulte pedidos sin un usuario, usando la clave compartida."""

    def has_permission(self, request, view):
        return es_servicio_interno(request)


class EsCliente(BasePermission):
    """Solo los clientes compran; un administrador no crea pedidos (spec.md, sección 4.2)."""

    message = "Solo un cliente puede crear pedidos."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and not request.user.is_staff)
