"""La documentación OpenAPI se genera y es pública (TP 4/5)."""

from django.core.cache import cache
from rest_framework.test import APITestCase


class DocumentacionTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_el_esquema_openapi_incluye_los_endpoints(self):
        r = self.client.get("/swagger.json")
        self.assertEqual(r.status_code, 200)
        esquema = r.json()

        # drf-yasg agrupa el prefijo común "/api" en basePath (formato OpenAPI 2)
        self.assertEqual(esquema["basePath"], "/api")
        rutas = esquema["paths"]
        self.assertIn("/orders/", rutas)
        self.assertIn("/token/", rutas)
        self.assertIn("/auth/register/", rutas)

    def test_la_interfaz_swagger_responde(self):
        self.assertEqual(self.client.get("/swagger/").status_code, 200)
        self.assertEqual(self.client.get("/redoc/").status_code, 200)