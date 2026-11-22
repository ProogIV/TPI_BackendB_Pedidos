from django.contrib import admin

from .models import Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "producto_id", "cantidad", "monto_total", "estado", "activo", "creado")
    list_filter = ("estado", "activo")
    search_fields = ("producto_id", "transaccion_id")
    # El total y el comprobante no se editan a mano: los calcula el sistema
    readonly_fields = ("monto_total", "transaccion_id", "creado", "actualizado")
