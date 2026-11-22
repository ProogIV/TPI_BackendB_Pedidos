from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


def rol_de(usuario):
    """ADMIN si es staff de Django; CLIENTE en cualquier otro caso (spec.md, sección 2.4)."""
    return "ADMIN" if usuario.is_staff else "CLIENTE"


class RegisterSerializer(serializers.ModelSerializer):
    """Registro de clientes (Clase 6). Nadie puede registrarse como administrador desde la API."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese email.")
        return value.lower()

    def create(self, validated_data):
        # create_user HASHEA la contraseña; nunca se guarda en texto plano (Clase 6)
        return User.objects.create_user(**validated_data)


class TokenConRolSerializer(TokenObtainPairSerializer):
    """
    Login que agrega el rol y el nombre de usuario dentro del token.

    Así Inventario puede saber si quien llama es ADMIN o CLIENTE leyendo el token, sin tener
    que consultar a Pedidos (spec.md, sección 7). El payload NO está cifrado, solo firmado:
    nunca se meten datos sensibles (Clase 6).
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["rol"] = rol_de(user)
        token["username"] = user.username
        return token
