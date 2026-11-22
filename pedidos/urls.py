from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# El router arma las rutas del ViewSet: /orders/ y /orders/<id>/ (Clase 4)
router = DefaultRouter()
router.register("orders", views.PedidoViewSet, basename="pedido")

urlpatterns = [
    path("health/", views.health_check, name="health_check"),
    path("", include(router.urls)),
]
