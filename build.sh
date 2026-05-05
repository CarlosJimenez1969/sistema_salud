#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

echo "=== Verificando variables de superuser ==="
echo "DJANGO_SUPERUSER_USERNAME está $([ -n "$DJANGO_SUPERUSER_USERNAME" ] && echo "definida" || echo "VACÍA")"
echo "DJANGO_SUPERUSER_EMAIL está $([ -n "$DJANGO_SUPERUSER_EMAIL" ] && echo "definida" || echo "VACÍA")"
echo "DJANGO_SUPERUSER_PASSWORD está $([ -n "$DJANGO_SUPERUSER_PASSWORD" ] && echo "definida" || echo "VACÍA")"

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "=== Ejecutando creación/actualización de superuser ==="
    python create_superuser.py
    echo "=== Fin de creación de superuser ==="
else
    echo "=== Omitido: faltan variables de entorno ==="
fi