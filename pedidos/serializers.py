import re

from rest_framework import serializers

from .models import Pedido

# Un _id de MongoDB son 24 caracteres hexadecimales (0-9, a-f)
OBJECT_ID_REGEX = re.compile(r"^[0-9a-fA-F]{24}$")


class PedidoSerializer(serializers.ModelSerializer):
    """
    Traduce Pedido <-> JSON y valida la entrada (Clases 3 y 4).

    El cliente solo puede enviar producto_id y cantidad: el precio lo informa Inventario,
    el total se calcula y el estado lo maneja el flujo de compra (spec.md, sección 4.2).
    """

    cliente = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id",
            "cliente",
            "producto_id",
            "cantidad",
            "precio_unitario",
            "monto_total",
            "estado",
            "transaccion_id",
            "creado",
        ]
        read_only_fields = [
            "id",
            "cliente",
            "precio_unitario",
            "monto_total",
            "estado",
            "transaccion_id",
            "creado",
        ]

    def validate_producto_id(self, value):
        if not OBJECT_ID_REGEX.match(value):
            raise serializers.ValidationError(
                "El producto_id debe ser un ID de MongoDB válido (24 caracteres hexadecimales)."
            )
        return value.lower()

    def validate_cantidad(self, value):
        if value < 1:
            raise serializers.ValidationError("La cantidad debe ser al menos 1.")
        return value
