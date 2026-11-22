from django.contrib import admin

from .models import Pedido, SecurityLog


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "producto_id", "cantidad", "monto_total", "estado", "activo", "creado")
    list_filter = ("estado", "activo")
    search_fields = ("producto_id", "transaccion_id")
    # El total y el comprobante no se editan a mano: los calcula el sistema
    readonly_fields = ("monto_total", "transaccion_id", "creado", "actualizado")


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ("creado", "accion", "detalle", "ip", "usuario")
    list_filter = ("accion",)
    search_fields = ("detalle", "ip")
    # Un registro de auditoría no se edita: solo se consulta
    readonly_fields = ("creado", "accion", "detalle", "ip", "usuario")
