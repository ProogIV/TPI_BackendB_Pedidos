from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import EsCliente
from .repositories import PedidoRepository
from .serializers import PedidoSerializer
from .serializers_auth import RegisterSerializer, TokenConRolSerializer
from .services import PedidoService


def health_check(request):
    """Confirma que el servicio está vivo. Es una vista de Django común: no requiere token."""
    return JsonResponse({"status": "ok", "service": "pedidos"})


# --- Autenticación (Clase 6) ---

class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ → crea un CLIENTE. Abierto: para registrarse no hay token."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    """POST /api/token/ → devuelve access y refresh; el access incluye el rol."""

    serializer_class = TokenConRolSerializer


# --- Pedidos ---

class PedidoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/orders/       → el CLIENTE ve sus pedidos; el ADMIN, todos
    GET  /api/orders/{id}/  → detalle (404 si el pedido es de otro cliente)
    POST /api/orders/       → solo CLIENTE: crea un pedido y ejecuta el flujo de compra

    No usa ModelViewSet completo a propósito: los pedidos son registros financieros y no tienen
    PUT ni DELETE (spec.md, sección 4.2).
    """

    serializer_class = PedidoSerializer
    filterset_fields = ["estado", "producto_id"]
    ordering_fields = ["creado", "monto_total"]

    def get_queryset(self):
        return PedidoRepository.visibles_para(self.request.user)

    def get_permissions(self):
        # Todo exige estar autenticado (configuración global); crear, además, ser cliente
        if self.action == "create":
            return [permissions.IsAuthenticated(), EsCliente()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        # La vista solo valida la entrada y arma la respuesta HTTP: el flujo vive en el servicio
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pedido = PedidoService.crear_pedido(cliente=request.user, **serializer.validated_data)

        return Response(self.get_serializer(pedido).data, status=status.HTTP_201_CREATED)
