from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from pedidos.views import LoginView, RegisterView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("pedidos.urls")),
    # Autenticación (Clase 6, spec.md sección 4.2)
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/token/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Botones "Log in / Log out" de la Browsable API
    path("api-auth/", include("rest_framework.urls")),
]
