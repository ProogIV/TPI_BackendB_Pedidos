from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from .models import Pedido
from .serializers import PedidoSerializer

PRODUCTO_ID = "665f1c2a9b1e8a0012345678"


def crear_pedido(**datos):
    valores = {
        "producto_id": PRODUCTO_ID,
        "cantidad": 2,
        "precio_unitario": Decimal("185000.00"),
    }
    valores.update(datos)
    return Pedido.objects.create(**valores)


class PedidoModeloTests(APITestCase):
    def test_monto_total_se_calcula_solo(self):
        pedido = crear_pedido(cantidad=3, precio_unitario=Decimal("1000.50"))
        self.assertEqual(pedido.monto_total, Decimal("3001.50"))

    def test_estado_inicial_es_pendiente(self):
        self.assertEqual(crear_pedido().estado, Pedido.Estado.PENDIENTE)

    def test_la_base_rechaza_cantidad_cero(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            crear_pedido(cantidad=0)


class PedidoSerializerTests(APITestCase):
    def test_rechaza_producto_id_invalido(self):
        serializer = PedidoSerializer(data={"producto_id": "no-es-un-id", "cantidad": 1})
        self.assertFalse(serializer.is_valid())
        self.assertIn("producto_id", serializer.errors)

    def test_ignora_campos_que_calcula_el_sistema(self):
        serializer = PedidoSerializer(data={
            "producto_id": PRODUCTO_ID,
            "cantidad": 1,
            "monto_total": "1.00",
            "estado": "PAGADO",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("monto_total", serializer.validated_data)
        self.assertNotIn("estado", serializer.validated_data)


class PedidoApiTests(APITestCase):
    def setUp(self):
        # Desde el TP 2 la API exige token: estos tests consultan como ADMIN, que ve todos los pedidos
        self.admin = User.objects.create_user("admin", password="clave-segura-123", is_staff=True)
        self.client.force_authenticate(self.admin)

    def test_lista_paginada_del_mas_nuevo_al_mas_viejo(self):
        primero = crear_pedido()
        segundo = crear_pedido()

        respuesta = self.client.get("/api/orders/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["count"], 2)
        ids = [p["id"] for p in respuesta.data["results"]]
        self.assertEqual(ids, [segundo.id, primero.id])

    def test_no_lista_pedidos_inactivos(self):
        crear_pedido(activo=False)
        respuesta = self.client.get("/api/orders/")
        self.assertEqual(respuesta.data["count"], 0)

    def test_filtra_por_estado_y_por_producto(self):
        crear_pedido(estado=Pedido.Estado.PAGADO)
        crear_pedido(estado=Pedido.Estado.FALLIDO)
        crear_pedido(producto_id="aaaaaaaaaaaaaaaaaaaaaaaa", estado=Pedido.Estado.PAGADO)

        pagados = self.client.get("/api/orders/?estado=PAGADO")
        self.assertEqual(pagados.data["count"], 2)

        del_producto = self.client.get(f"/api/orders/?producto_id={PRODUCTO_ID}")
        self.assertEqual(del_producto.data["count"], 2)

    def test_detalle_de_un_pedido(self):
        pedido = crear_pedido()
        respuesta = self.client.get(f"/api/orders/{pedido.id}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["monto_total"], "370000.00")

    def test_pedido_inexistente_responde_404_con_formato_uniforme(self):
        respuesta = self.client.get("/api/orders/9999/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(respuesta.data["error"])
        self.assertIn("mensaje", respuesta.data)

    def test_no_permite_modificar_ni_borrar_pedidos(self):
        pedido = crear_pedido()
        self.assertEqual(self.client.put(f"/api/orders/{pedido.id}/", {}).status_code, 405)
        self.assertEqual(self.client.delete(f"/api/orders/{pedido.id}/").status_code, 405)
