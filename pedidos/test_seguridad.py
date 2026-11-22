"""Tests de seguridad (TP 2, Clase 8): rate limiting, auditoría y CORS."""

from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APITestCase

from .models import SecurityLog

CLAVE = "clave-segura-123"


class RateLimitingTests(APITestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user("ana", password=CLAVE)

    def login(self, password):
        return self.client.post("/api/token/", {"username": "ana", "password": password}, format="json")

    def test_el_sexto_intento_de_login_en_un_minuto_responde_429(self):
        for _ in range(5):
            self.assertEqual(self.login("incorrecta").status_code, 401)

        r = self.login("incorrecta")

        self.assertEqual(r.status_code, 429)
        self.assertTrue(r.data["error"])
        self.assertIn("Retry-After", r.headers)

    def test_el_limite_frena_incluso_con_la_clave_correcta(self):
        # Una vez superado el límite, ni la clave correcta pasa: así un ataque no puede seguir probando
        for _ in range(5):
            self.login("incorrecta")
        self.assertEqual(self.login(CLAVE).status_code, 429)

    def test_limite_general_para_anonimos(self):
        # El registro es público: lo protege el límite de 20 peticiones por minuto por IP
        for _ in range(20):
            self.client.post("/api/auth/register/", {}, format="json")
        r = self.client.post("/api/auth/register/", {}, format="json")
        self.assertEqual(r.status_code, 429)


class AuditoriaTests(APITestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user("ana", password=CLAVE)

    def test_un_login_fallido_queda_registrado_sin_la_clave(self):
        self.client.post("/api/token/", {"username": "ana", "password": "clave-mal-escrita"}, format="json")

        registro = SecurityLog.objects.get()
        self.assertEqual(registro.accion, "login_fallido")
        self.assertEqual(registro.detalle, "usuario=ana")
        self.assertEqual(registro.ip, "127.0.0.1")
        self.assertNotIn("clave-mal-escrita", registro.detalle)  # nunca se guarda la contraseña

    def test_un_login_exitoso_no_genera_registro(self):
        self.client.post("/api/token/", {"username": "ana", "password": CLAVE}, format="json")
        self.assertEqual(SecurityLog.objects.count(), 0)

    def test_el_intento_frenado_por_el_limite_no_llega_a_registrarse(self):
        # Como en la Clase 8: el sexto intento lo corta el throttle antes de verificar la clave
        for _ in range(6):
            self.client.post("/api/token/", {"username": "ana", "password": "mal"}, format="json")
        self.assertEqual(SecurityLog.objects.count(), 5)


class CorsTests(APITestCase):
    def test_el_frontend_puede_leer_las_respuestas(self):
        r = self.client.get("/api/orders/", HTTP_ORIGIN="http://localhost:5500")
        self.assertEqual(r.headers.get("Access-Control-Allow-Origin"), "http://localhost:5500")

    def test_un_sitio_desconocido_no_recibe_permiso(self):
        r = self.client.get("/api/orders/", HTTP_ORIGIN="http://sitio-malicioso.com")
        self.assertNotIn("Access-Control-Allow-Origin", r.headers)
