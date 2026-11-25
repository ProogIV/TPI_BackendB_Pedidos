"""
Carga inicial de datos (planificación, punto 1.4): crea los usuarios de demostración si no existen.

Uso:  python manage.py seed
Se ejecuta solo al arrancar el contenedor (docker-compose.yml), después de migrate.
Es idempotente: si los usuarios ya existen, no hace nada.
"""

import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea los usuarios de demostración (un ADMIN y un CLIENTE) si no existen."

    def handle(self, *args, **options):
        usuarios = [
            {
                "username": os.getenv("DEMO_ADMIN_USERNAME", "admin"),
                "password": os.getenv("DEMO_ADMIN_PASSWORD", "Admin12345!"),
                "email": "admin@tpi.local",
                "es_admin": True,
            },
            {
                "username": os.getenv("DEMO_CLIENTE_USERNAME", "cliente"),
                "password": os.getenv("DEMO_CLIENTE_PASSWORD", "Cliente12345!"),
                "email": "cliente@tpi.local",
                "es_admin": False,
            },
        ]

        for datos in usuarios:
            if User.objects.filter(username=datos["username"]).exists():
                self.stdout.write(f"[seed] El usuario '{datos['username']}' ya existe.")
                continue

            if datos["es_admin"]:
                User.objects.create_superuser(datos["username"], datos["email"], datos["password"])
            else:
                User.objects.create_user(datos["username"], datos["email"], datos["password"])
            self.stdout.write(self.style.SUCCESS(f"[seed] Usuario '{datos['username']}' creado."))
