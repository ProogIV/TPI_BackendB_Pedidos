from django.http import JsonResponse
from rest_framework import mixins, viewsets

from .repositories import PedidoRepository
from .serializers import PedidoSerializer


def health_check(request):
    """Confirma que el servicio está vivo. Es una vista de Django común: no requiere token."""
    return JsonResponse({"status": "ok", "service": "pedidos"})


class PedidoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET /api/orders/       → listado paginado, con filtros ?estado= y ?producto_id=
    GET /api/orders/{id}/  → detalle de un pedido

    No usa ModelViewSet completo a propósito: los pedidos son registros financieros y no tienen
    PUT ni DELETE (spec.md, sección 4.2). El POST con el flujo de compra se agrega en la parte 3.
    """

    serializer_class = PedidoSerializer
    filterset_fields = ["estado", "producto_id"]
    ordering_fields = ["creado", "monto_total"]

    def get_queryset(self):
        return PedidoRepository.get_queryset()
