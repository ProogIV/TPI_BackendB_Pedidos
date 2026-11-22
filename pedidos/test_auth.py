"""Tests de autenticación y roles (TP 2, Clases 6 y 7)."""

from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from .models import Pedido

CLAVE = "clave-segura-123"
PRODUCTO_ID = "665f1c2a9b1e8a0012345678"


def crear_pedido(cliente):
    return Pedido.objects.create(
        cliente=cliente, producto_id=PRODUCTO_ID, cantidad=1, precio_unitario=Decimal("100.00")
    )


class RegistroTests(APITestCase):
    def test_registro_crea_un_cliente_con_la_clave_hasheada(self):
        r = self.client.post(
            "/api/auth/register/",
            {"username": "ana", "email": "Ana@Ejemplo.com", "password": CLAVE},
            format="json",
        )

        self.assertEqual(r.status_code, 201)
        self.assertNotIn("password", r.data)
        usuario = User.objects.get(username="ana")
        self.assertFalse(usuario.is_staff)
        self.assertEqual(usuario.email, "ana@ejemplo.com")
        self.assertNotEqual(usuario.password, CLAVE)  # se guarda el hash, no la clave
        self.assertTrue(usuario.check_password(CLAVE))

    def test_rechaza_una_clave_debil(self):
        r = self.client.post(
            "/api/auth/register/",
            {"username": "ana", "email": "ana@ejemplo.com", "password": "123"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("password", r.data["detalles"])

    def test_rechaza_un_email_repetido(self):
        User.objects.create_user("ana", email="ana@ejemplo.com", password=CLAVE)
        r = self.client.post(
            "/api/auth/register/",
            {"username": "otra", "email": "ANA@ejemplo.com", "password": CLAVE},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.data["detalles"])

    def test_no_se_puede_registrar_un_admin(self):
        self.client.post(
            "/api/auth/register/",
            {"username": "pillo", "email": "p@x.com", "password": CLAVE, "is_staff": True},
            format="json",
        )
        self.assertFalse(User.objects.get(username="pillo").is_staff)


class LoginTests(APITestCase):
    def login(self, username):
        return self.client.post("/api/token/", {"username": username, "password": CLAVE}, format="json")

    def test_el_token_del_cliente_dice_rol_cliente(self):
        User.objects.create_user("ana", password=CLAVE)
        r = self.login("ana")

        self.assertEqual(r.status_code, 200)
        self.assertIn("refresh", r.data)
        token = AccessToken(r.data["access"])
        self.assertEqual(token["rol"], "CLIENTE")
        self.assertEqual(token["username"], "ana")

    def test_el_token_del_admin_dice_rol_admin(self):
        User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        token = AccessToken(self.login("jefe").data["access"])
        self.assertEqual(token["rol"], "ADMIN")

    def test_login_con_clave_incorrecta_responde_401(self):
        User.objects.create_user("ana", password=CLAVE)
        r = self.client.post("/api/token/", {"username": "ana", "password": "mal"}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertTrue(r.data["error"])

    def test_con_el_token_se_puede_consultar_la_api(self):
        User.objects.create_user("ana", password=CLAVE)
        access = self.login("ana").data["access"]

        r = self.client.get("/api/orders/", HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(r.status_code, 200)


class RolesTests(APITestCase):
    def setUp(self):
        self.ana = User.objects.create_user("ana", password=CLAVE)
        self.beto = User.objects.create_user("beto", password=CLAVE)
        self.admin = User.objects.create_user("jefe", password=CLAVE, is_staff=True)
        self.pedido_ana = crear_pedido(self.ana)
        self.pedido_beto = crear_pedido(self.beto)

    def test_sin_token_responde_401_con_formato_uniforme(self):
        r = self.client.get("/api/orders/")
        self.assertEqual(r.status_code, 401)
        self.assertTrue(r.data["error"])

    def test_token_inventado_responde_401(self):
        r = self.client.get("/api/orders/", HTTP_AUTHORIZATION="Bearer cualquiercosa")
        self.assertEqual(r.status_code, 401)
        self.assertTrue(r.data["error"])
        self.assertNotIn("detalles", r.data)  # es un error de autenticación, no de validación

    def test_el_health_sigue_siendo_publico(self):
        self.assertEqual(self.client.get("/api/health/").status_code, 200)

    def test_el_cliente_solo_ve_sus_pedidos(self):
        self.client.force_authenticate(self.ana)
        r = self.client.get("/api/orders/")
        self.assertEqual([p["id"] for p in r.data["results"]], [self.pedido_ana.id])

    def test_el_pedido_de_otro_cliente_responde_404(self):
        # Defensa contra IDOR (Clase 6): el pedido ajeno "no existe" para este cliente
        self.client.force_authenticate(self.ana)
        r = self.client.get(f"/api/orders/{self.pedido_beto.id}/")
        self.assertEqual(r.status_code, 404)

    def test_el_admin_ve_todos_los_pedidos(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/orders/")
        self.assertEqual(r.data["count"], 2)

    def test_el_admin_no_puede_crear_pedidos(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post("/api/orders/", {"producto_id": PRODUCTO_ID, "cantidad": 1}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["mensaje"], "Solo un cliente puede crear pedidos.")
