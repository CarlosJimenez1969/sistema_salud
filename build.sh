#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Crear superuser automáticamente si las variables de entorno están definidas
if [[ -n "$DJANGO_SUPERUSER_USERNAME" && -n "$DJANGO_SUPERUSER_EMAIL" && -n "$DJANGO_SUPERUSER_PASSWORD" ]]; then
    python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
username = os.environ['DJANGO_SUPERUSER_USERNAME']
email    = os.environ['DJANGO_SUPERUSER_EMAIL']
password = os.environ['DJANGO_SUPERUSER_PASSWORD']
cedula   = os.environ.get('DJANGO_SUPERUSER_CEDULA', '0000000000')
u = User.objects.filter(email=email).first()
if u:
    u.set_password(password)
    u.is_superuser = True
    u.is_staff = True
    u.is_active = True
    u.role = 'ADMIN'
    u.save()
    print(f'Superuser actualizado: {email}')
else:
    User.objects.create_superuser(username=username, email=email, password=password, cedula=cedula, role='ADMIN')
    print(f'Superuser creado: {email}')
"
fi