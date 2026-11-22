from django.http import JsonResponse


def health_check(request):
    """Confirma que el servicio está vivo. Es una vista de Django común: no requiere token."""
    return JsonResponse({"status": "ok", "service": "pedidos"})
