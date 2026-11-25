"""Tests del acceso de Inventario a Pedidos con X-Service-Token (spec.md, sección 7)."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import Pedido

PRODUCTO_ID = "665f1c2a9b1e8a0012345678"


@override_settings(SERVICE_TOKEN="token-de-prueba")
class AccesoDeServicioTests(APITestCase):
    def setUp(self):
        cache.clear()
        ana = User.objects.create_user("ana", password="clave-segura-123")
        beto = User.objects.create_user("beto", password="clave-segura-123")
        for cliente in (ana, beto):
            Pedido.objects.create(
                cliente=cliente, producto_id=PRODUCTO_ID, cantidad=1, precio_unitario=Decimal("100.00")
            )

    def test_inventario_consulta_los_pedidos_de_un_producto_con_la_clave(self):
        r = self.client.get(f"/api/orders/?producto_id={PRODUCTO_ID}", HTTP_X_SERVICE_TOKEN="token-de-prueba")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)  # ve los pedidos de todos los clientes

    def test_con_una_clave_incorrecta_responde_401(self):
        r = self.client.get("/api/orders/", HTTP_X_SERVICE_TOKEN="clave-incorrecta")
        self.assertEqual(r.status_code, 401)

    def test_la_clave_de_servicio_no_sirve_para_comprar(self):
        r = self.client.post(
            "/api/orders/",
            {"producto_id": PRODUCTO_ID, "cantidad": 1},
            format="json",
            HTTP_X_SERVICE_TOKEN="token-de-prueba",
        )
        self.assertIn(r.status_code, (401, 403))
        self.assertEqual(Pedido.objects.count(), 2)

    @override_settings(SERVICE_TOKEN="")
    def test_sin_clave_configurada_nadie_entra_como_servicio(self):
        r = self.client.get("/api/orders/", HTTP_X_SERVICE_TOKEN="")
        self.assertEqual(r.status_code, 401)
