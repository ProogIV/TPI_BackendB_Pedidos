from rest_framework.permissions import BasePermission


class EsCliente(BasePermission):
    """Solo los clientes compran; un administrador no crea pedidos (spec.md, sección 4.2)."""

    message = "Solo un cliente puede crear pedidos."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and not request.user.is_staff)
