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

## Estructura

```
manage.py
config/              → configuración del proyecto (settings, urls, asgi, wsgi)
pedidos/             → app del dominio
  views.py           → capa HTTP
  exceptions.py      → manejador centralizado con el formato de error del spec
  urls.py
```

## Estado

| Entrega | Contenido | Estado |
|---|---|---|
| TP 1 | Configuración base, `.env`, DRF, health check, errores uniformes | ✅ |
| TP 1 | Modelo Pedido, flujo de compra con Inventario | En curso |
| TP 2 | JWT, roles, rate limiting, CORS | Pendiente |
| TP 3 | Integración con Pagos y WebSockets | Pendiente |
| TP 4/5 | PostgreSQL, Daphne, Docker, OpenAPI, GraphQL | Pendiente |
