from .models import Pedido


class PedidoRepository:
    """Capa de acceso a datos (Clase 5): todas las consultas de pedidos pasan por acá."""

    @staticmethod
    def get_queryset():
        # Solo activos (borrado lógico) y con orden estable para paginar (Clase 5)
        return (
            Pedido.objects.filter(activo=True)
            .select_related("cliente")
            .order_by("-creado", "-id")
        )

    @staticmethod
    def crear(**datos):
        return Pedido.objects.create(**datos)

    @staticmethod
    def actualizar_estado(pedido, estado, transaccion_id=None):
        pedido.estado = estado
        pedido.transaccion_id = transaccion_id
        pedido.save(update_fields=["estado", "transaccion_id", "actualizado"])
        return pedido
