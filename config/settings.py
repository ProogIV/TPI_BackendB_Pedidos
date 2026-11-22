"""
Configuración del servicio de Pedidos (TPI Programación IV).

Todos los valores que cambian según el entorno (desarrollo, tests, Docker) o que son secretos
se leen del archivo .env con python-dotenv, como en la Clase 1. En este archivo no hay ningún
valor sensible escrito.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")


# --- Aplicaciones ---

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    # Propias
    "pedidos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# --- Base de datos ---
# Sin DB_ENGINE (o con DB_ENGINE=sqlite) se usa SQLite, ideal para desarrollar.
# Con DB_ENGINE=postgresql se leen las credenciales del entorno (Clase 12): así el mismo código
# funciona en la PC de cada uno y en Docker, cambiando solo el .env.

DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")

if DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": f"django.db.backends.{DB_ENGINE}",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT"),
        }
    }


# --- Contraseñas ---

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Idioma y zona horaria ---
# "es" hace que Django y DRF traduzcan solos sus mensajes de error (Clase 4b).

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True


# --- Archivos estáticos ---

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Django REST Framework ---

REST_FRAMEWORK = {
    # Formato uniforme de errores del spec: {"error": true, "mensaje": ...} (Clase 4)
    "EXCEPTION_HANDLER": "pedidos.exceptions.custom_exception_handler",
    # Autenticación con JWT (Clase 6). La sesión queda solo para usar la Browsable API.
    # El orden importa: con JWT primero, una petición sin token recibe 401 y no 403.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Seguro por defecto: toda la API exige estar autenticado salvo lo que se abra a propósito
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Paginación y filtros (Clase 5)
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
}


# --- Servicios con los que se comunica Pedidos (spec.md, sección 1) ---

INVENTARIO_API_URL = os.getenv("INVENTARIO_API_URL", "http://127.0.0.1:3000/api")
PAGOS_API_URL = os.getenv("PAGOS_API_URL", "http://127.0.0.1:8001/api")
TIMEOUT_SERVICIOS = 5  # segundos (spec.md, regla 7)


# --- JWT (Clase 6, spec.md sección 7) ---
# Pedidos es el único servicio que emite tokens. Inventario los valida con la MISMA clave
# (JWT_SIGNING_KEY), por eso se lee del .env y no es la SECRET_KEY de Django.

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.getenv("JWT_SIGNING_KEY", SECRET_KEY),
}
