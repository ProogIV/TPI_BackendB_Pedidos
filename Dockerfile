# Microservicio Backend B - Pedidos (Python + Django + ASGI/Daphne)
FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilación y cliente PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código fuente del proyecto Django
COPY . .

# Puerto expuesto para HTTP y WebSockets
EXPOSE 8000

ENV PYTHONUNBUFFERED=1

# Servidor ASGI Daphne para producción (soporta HTTP y WebSockets del TP 3)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
