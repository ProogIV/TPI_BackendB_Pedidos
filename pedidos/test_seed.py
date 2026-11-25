from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase


class SeedTests(TestCase):
    def test_crea_un_admin_y_un_cliente(self):
        call_command("seed")

        admin = User.objects.get(username="admin")
        cliente = User.objects.get(username="cliente")
        self.assertTrue(admin.is_staff)
        self.assertFalse(cliente.is_staff)
        self.assertTrue(cliente.check_password("Cliente12345!"))

    def test_es_idempotente(self):
        call_command("seed")
        call_command("seed")
        self.assertEqual(User.objects.count(), 2)
