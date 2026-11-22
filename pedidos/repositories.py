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
    def visibles_para(usuario):
        """
        El ADMIN ve todos los pedidos; el CLIENTE, solo los suyos (spec.md, sección 4.2).

        Filtrar desde el origen evita el IDOR (Clase 6): para la API, los pedidos ajenos
        directamente no existen y su detalle responde 404.
        """
        pedidos = PedidoRepository.get_queryset()
        if usuario.is_staff:
            return pedidos
        return pedidos.filter(cliente=usuario)

    @staticmethod
    def crear(**datos):
        return Pedido.objects.create(**datos)

    @staticmethod
    def actualizar_estado(pedido, estado, transaccion_id=None):
        pedido.estado = estado
        pedido.transaccion_id = transaccion_id
        pedido.save(update_fields=["estado", "transaccion_id", "actualizado"])
        return pedido
