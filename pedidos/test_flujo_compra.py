"""
Tests del flujo de compra (spec.md, sección 5).

Inventario y Pagos se reemplazan por respuestas simuladas con unittest.mock (librería estándar
de Python): así los tests no necesitan los otros servicios corriendo ni conexión de red.
"""

from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APITestCase

from .models import Pedido

PRODUCTO_ID = "665f1c2a9b1e8a0012345678"
URL = "/api/orders/"


def respuesta(status_code, datos=None):
    """Simula una respuesta de requests con su código y su JSON."""
    simulada = Mock()
    simulada.status_code = status_code
    simulada.json.return_value = datos or {}
    return simulada


DESCUENTO_OK = respuesta(200, {"_id": PRODUCTO_ID, "nombre": "Placa de Video", "precio": 185000, "stock": 13})
PAGO_APROBADO = respuesta(200, {"estado": "APROBADO", "transaccion_id": "tx-123", "mensaje": "Pago aprobado"})
PAGO_RECHAZADO = respuesta(200, {"estado": "RECHAZADO", "transaccion_id": None, "mensaje": "Supera el límite"})
REPOSICION_OK = respuesta(200, {"_id": PRODUCTO_ID, "stock": 15})


def inventario_simulado(descuento, reposicion=REPOSICION_OK):
    """Devuelve una respuesta distinta según si se llama a /descontar o a /reponer."""
    def responder(url, **kwargs):
        if url.endswith("/descontar"):
            if isinstance(descuento, Exception):
                raise descuento
            return descuento
        return reposicion
    return responder


@patch("pedidos.services.requests.post")
@patch("pedidos.services.requests.patch")
class FlujoDeCompraTests(APITestCase):

    def setUp(self):
        cache.clear()  # reinicia los contadores del rate limiting entre tests
        # Desde el TP 2 solo un CLIENTE autenticado puede comprar
        self.cliente = User.objects.create_user("ana", password="clave-segura-123")
        self.client.force_authenticate(self.cliente)

    def comprar(self, cantidad=2):
        return self.client.post(URL, {"producto_id": PRODUCTO_ID, "cantidad": cantidad}, format="json")

    def test_compra_exitosa_queda_pagada(self, mock_patch, mock_post):
        mock_patch.side_effect = inventario_simulado(DESCUENTO_OK)
        mock_post.return_value = PAGO_APROBADO

        r = self.comprar(cantidad=2)

        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["estado"], "PAGADO")
        self.assertEqual(r.data["transaccion_id"], "tx-123")
        self.assertEqual(r.data["precio_unitario"], "185000.00")
        self.assertEqual(r.data["monto_total"], "370000.00")

        # Se pidió a Inventario descontar la cantidad correcta, con timeout de 5 s (regla 7)
        url, kwargs = mock_patch.call_args.args[0], mock_patch.call_args.kwargs
        self.assertTrue(url.endswith(f"/productos/{PRODUCTO_ID}/descontar"))
        self.assertEqual(kwargs["json"], {"cantidad": 2})
        self.assertEqual(kwargs["timeout"], 5)

        # El pedido quedó a nombre del cliente autenticado
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.cliente, self.cliente)

        # Se pidió a Pagos cobrar el monto total del pedido creado
        self.assertEqual(mock_post.call_args.kwargs["json"], {"order_id": pedido.id, "monto": 370000.0})

    def test_sin_stock_no_se_crea_el_pedido_ni_se_cobra(self, mock_patch, mock_post):
        mock_patch.side_effect = inventario_simulado(
            respuesta(400, {"error": True, "mensaje": "Stock insuficiente. Disponible: 1"})
        )

        r = self.comprar(cantidad=5)

        self.assertEqual(r.status_code, 400)
        self.assertTrue(r.data["error"])
        self.assertEqual(r.data["mensaje"], "Stock insuficiente. Disponible: 1")
        self.assertEqual(Pedido.objects.count(), 0)
        mock_post.assert_not_called()

    def test_producto_inexistente_responde_404(self, mock_patch, mock_post):
        mock_patch.side_effect = inventario_simulado(
            respuesta(404, {"error": True, "mensaje": "Producto no encontrado"})
        )

        r = self.comprar()

        self.assertEqual(r.status_code, 404)
        self.assertEqual(Pedido.objects.count(), 0)
        mock_post.assert_not_called()

    def test_inventario_caido_responde_503(self, mock_patch, mock_post):
        mock_patch.side_effect = inventario_simulado(requests.ConnectionError())

        r = self.comprar()

        self.assertEqual(r.status_code, 503)
        self.assertIn("Inventario", r.data["mensaje"])
        self.assertEqual(Pedido.objects.count(), 0)

    def test_pago_rechazado_queda_fallido_y_repone_stock(self, mock_patch, mock_post):
        mock_patch.side_effect = inventario_simulado(DESCUENTO_OK)
        mock_post.return_value = PAGO_RECHAZADO

        r = self.comprar(cantidad=2)

        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["estado"], "FALLIDO")
        self.assertIsNone(r.data["transaccion_id"])

        urls_llamadas = [llamada.args[0] for llamada in mock_patch.call_args_list]
        self.assertTrue(urls_llamadas[-1].endswith(f"/productos/{PRODUCTO_ID}/reponer"))
        self.assertEqual(mock_patch.call_args_list[-1].kwargs["json"], {"cantidad": 2})

    def test_pagos_caido_queda_fallido_y_repone_stock(self, mock_patch, mock_post):
        mock_patch.side_effect = inventario_simulado(DESCUENTO_OK)
        mock_post.side_effect = requests.Timeout()

        r = self.comprar()

        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["estado"], "FALLIDO")
        self.assertTrue(mock_patch.call_args_list[-1].args[0].endswith("/reponer"))

    def test_datos_invalidos_no_llaman_a_inventario(self, mock_patch, mock_post):
        r = self.client.post(URL, {"producto_id": PRODUCTO_ID, "cantidad": 0}, format="json")

        self.assertEqual(r.status_code, 400)
        self.assertIn("cantidad", r.data["detalles"])
        mock_patch.assert_not_called()

    def test_el_cliente_no_puede_fijar_precio_ni_estado(self, mock_patch, mock_post):
        mock_patch.side_effect = inventario_simulado(DESCUENTO_OK)
        mock_post.return_value = PAGO_RECHAZADO

        r = self.client.post(URL, {
            "producto_id": PRODUCTO_ID,
            "cantidad": 1,
            "precio_unitario": "1.00",
            "estado": "PAGADO",
        }, format="json")

        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["precio_unitario"], "185000.00")
        self.assertEqual(r.data["estado"], "FALLIDO")
