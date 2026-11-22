from django.http import JsonResponse
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from .repositories import PedidoRepository
from .serializers import PedidoSerializer
from .services import PedidoService


def health_check(request):
    """Confirma que el servicio está vivo. Es una vista de Django común: no requiere token."""
    return JsonResponse({"status": "ok", "service": "pedidos"})


class PedidoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/orders/       → listado paginado, con filtros ?estado= y ?producto_id=
    GET  /api/orders/{id}/  → detalle de un pedido
    POST /api/orders/       → crea un pedido y ejecuta el flujo de compra

    No usa ModelViewSet completo a propósito: los pedidos son registros financieros y no tienen
    PUT ni DELETE (spec.md, sección 4.2).
    """

    serializer_class = PedidoSerializer
    filterset_fields = ["estado", "producto_id"]
    ordering_fields = ["creado", "monto_total"]

    def get_queryset(self):
        return PedidoRepository.get_queryset()

    def create(self, request, *args, **kwargs):
        # La vista solo valida la entrada y arma la respuesta HTTP: el flujo vive en el servicio
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cliente = request.user if request.user.is_authenticated else None  # TP 2: obligatorio
        pedido = PedidoService.crear_pedido(cliente=cliente, **serializer.validated_data)

        return Response(self.get_serializer(pedido).data, status=status.HTTP_201_CREATED)
