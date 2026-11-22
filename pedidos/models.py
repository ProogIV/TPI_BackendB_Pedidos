from django.conf import settings
from django.db import models
from django.db.models import Q


class Pedido(models.Model):
    """
    Orden de compra de un producto (spec.md, sección 2.3).

    El producto vive en MongoDB (servicio de Inventario): acá solo se guarda su _id como texto.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        FALLIDO = "FALLIDO", "Fallido"

    # En el TP 1 todavía no hay login, por eso puede ser nulo. En el TP 2 pasa a ser obligatorio.
    # PROTECT: no se puede borrar un usuario que tiene pedidos (son registros financieros).
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos",
        null=True,
        blank=True,
    )
    producto_id = models.CharField(max_length=24)
    cantidad = models.PositiveIntegerField()
    # Precio informado por Inventario al momento de la compra (spec.md, regla 5)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    transaccion_id = models.CharField(max_length=64, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]
        constraints = [
            # Restricciones en la propia base de datos: se cumplen aunque alguien
            # cree un pedido sin pasar por la API (por ejemplo, desde el admin).
            models.CheckConstraint(condition=Q(cantidad__gte=1), name="pedido_cantidad_minima_1"),
            models.CheckConstraint(condition=Q(precio_unitario__gte=0), name="pedido_precio_no_negativo"),
        ]

    def save(self, *args, **kwargs):
        # monto_total siempre se calcula: nunca lo manda el cliente (spec.md, sección 2.3)
        if self.precio_unitario is not None and self.cantidad is not None:
            self.monto_total = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pedido #{self.pk} — {self.cantidad} x {self.producto_id} ({self.estado})"


class SecurityLog(models.Model):
    """
    Registro de auditoría de eventos de seguridad (Clase 8): quién, qué, cuándo y desde dónde.

    Nunca se guardan contraseñas ni tokens, ni siquiera las contraseñas incorrectas.
    """

    # SET_NULL: si se borra el usuario, el registro de auditoría se conserva
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    accion = models.CharField(max_length=50)  # ej: "login_fallido"
    detalle = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "registro de seguridad"
        verbose_name_plural = "registros de seguridad"

    def __str__(self):
        return f"{self.creado:%Y-%m-%d %H:%M} {self.accion} ({self.ip})"
