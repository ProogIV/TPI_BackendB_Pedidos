from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """
    Límite estricto para el login: 5 intentos por minuto por IP (Clase 8).

    Se cuenta por IP porque en el login todavía no hay un usuario autenticado.
    Se limita el ritmo en lugar de bloquear la cuenta: si no, cualquiera podría bloquear
    la cuenta de otro con solo equivocarse 5 veces a propósito.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
