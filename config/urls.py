from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenRefreshView

from pedidos.views import LoginView, RegisterView

# Documentación automática OpenAPI (drf-yasg): se genera leyendo los serializers y las vistas
schema_view = get_schema_view(
    openapi.Info(
        title="TPI — Servicio de Pedidos",
        default_version="v1",
        description=(
            "Usuarios, autenticación JWT y órdenes de compra. "
            "Coordina el flujo de compra con Inventario y Pagos (ver spec.md)."
        ),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("pedidos.urls")),
    # Autenticación (Clase 6, spec.md sección 4.2)
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/token/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Botones "Log in / Log out" de la Browsable API
    path("api-auth/", include("rest_framework.urls")),
    # Documentación OpenAPI
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
