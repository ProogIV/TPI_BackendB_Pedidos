# TPI — Microservicio de Pedidos

Gestiona los usuarios y las órdenes de compra, y coordina el flujo de compra con Inventario y Pagos.
**Python + Django REST Framework + PostgreSQL** · Puerto **8000**

Forma parte del TPI de Programación IV (Equipo 12). La especificación completa del sistema
(`spec.md`) y las reglas técnicas (`agent.md`) están en el repositorio orquestador
[TPI_Ecommerce](https://github.com/ProogIV/TPI_Ecommerce).

## Requisitos

- Python 3.12 (la misma versión que usa la imagen de Docker)

## Puesta en marcha

```bash
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1        # Windows (PowerShell)
# source venv/bin/activate         # Linux / Mac
pip install -r requirements.txt
cp .env.example .env               # Windows: Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Verificar: `GET http://127.0.0.1:8000/api/health/` → `{"status": "ok", "service": "pedidos"}`.

## Autenticación (JWT)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/register/` | Registro de un cliente (`username`, `email`, `password`) |
| POST | `/api/token/` | Login: devuelve `access` y `refresh`. El `access` incluye el `rol` |
| POST | `/api/token/refresh/` | Renueva el `access` |

Todos los endpoints de `/api/orders/` exigen el header `Authorization: Bearer <access>`.
El **cliente** crea y ve solo sus pedidos; el **administrador** (`is_staff`) ve todos y no puede comprar.

Para crear un administrador: `python manage.py createsuperuser`.

## Seguridad (Clase 8)

| Medida | Detalle |
|---|---|
| Rate limiting en el login | 5 intentos por minuto por IP; el sexto responde `429` con el header `Retry-After` |
| Límites generales | 20 peticiones por minuto para anónimos (por IP) y 100 para usuarios autenticados |
| CORS | Solo los orígenes de `CORS_ALLOWED_ORIGINS` (el frontend) pueden leer las respuestas desde el navegador |
| Auditoría | Cada login fallido se guarda en el modelo `SecurityLog` (visible en `/admin/`) y en el archivo `security.log`, sin la contraseña |
| Acceso entre servicios | Inventario consulta `GET /api/orders/?producto_id=` con el header `X-Service-Token` (clave `SERVICE_TOKEN`); Pedidos manda la misma clave al descontar y reponer stock |
| Sanitización (`nh3`) | No se aplica: los pedidos no tienen campos de texto libre. Todos los datos de entrada se validan con formato estricto (ID de MongoDB, enteros positivos) |

## Endpoints de pedidos

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/orders/?estado=&producto_id=` | Pedidos visibles para el usuario (paginado) |
| GET | `/api/orders/{id}/` | Detalle (404 si es de otro cliente) |
| POST | `/api/orders/` | Crea un pedido y ejecuta el flujo de compra con Inventario y Pagos |

## Tests

```bash
python manage.py test
```

## Estructura

```
manage.py
config/                → configuración del proyecto (settings, urls, asgi, wsgi)
pedidos/               → app del dominio
  models.py            → modelo Pedido
  serializers.py       → validación de pedidos
  serializers_auth.py  → registro y login con rol
  repositories.py      → consultas (incluye qué pedidos ve cada usuario)
  services.py          → flujo de compra y llamadas a Inventario y Pagos
  permissions.py       → permisos por rol
  throttles.py         → límite de intentos del login
  views.py             → capa HTTP
  exceptions.py        → manejador centralizado con el formato de error del spec
```

## Decisiones fuera del contenido de la cátedra

| Decisión | Motivo |
|---|---|
| El token JWT incluye el `rol` (`ADMIN`/`CLIENTE`) y el `username` | Inventario valida el mismo token y necesita saber el rol sin consultar a Pedidos (spec.md, sección 7). Se agrega sobrescribiendo `get_token` del serializer de login de simplejwt. |
| Clave de firma propia (`JWT_SIGNING_KEY`) en lugar de la `SECRET_KEY` | La comparten Pedidos e Inventario; así la `SECRET_KEY` de Django no sale de este servicio. |
| `unittest.mock` en los tests del flujo de compra | Simula Inventario y Pagos para que los tests no dependan de otros servicios ni de la red, con el mismo objetivo que el `conftest.py` de la Clase 12. Es parte de la librería estándar de Python. |

## Estado

| Entrega | Contenido | Estado |
|---|---|---|
| TP 1 | Configuración base, `.env`, DRF, health check, errores uniformes | ✅ |
| TP 1 | Modelo Pedido, flujo de compra con Inventario | ✅ |
| TP 2 | JWT y roles | ✅ |
| TP 2 | Rate limiting, CORS, auditoría | ✅ |
| TP 3 | Integración con Pagos | ✅ |
| TP 3 | WebSockets | Pendiente |
| TP 4/5 | PostgreSQL, Daphne, Docker, OpenAPI, GraphQL | Pendiente |
