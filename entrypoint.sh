#!/usr/bin/env bash
set -euo pipefail

echo ">>> Recolectando archivos estaticos..."
python manage.py collectstatic --noinput

echo ">>> Aplicando migraciones..."
python manage.py migrate --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo ">>> Creando/actualizando superusuario..."
    python create_superuser.py || echo "[WARN] create_superuser falló (ignorado)"
fi

echo ">>> Iniciando Gunicorn..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --threads ${GUNICORN_THREADS:-2} \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --access-logfile - \
    --error-logfile -
