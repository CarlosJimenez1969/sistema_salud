"""
Script para crear/actualizar superusuario desde variables de entorno.
Se ejecuta desde build.sh durante el deploy.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '')
email    = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
cedula   = os.environ.get('DJANGO_SUPERUSER_CEDULA', '0000000000')

if not (username and email and password):
    print("[SUPERUSER] Variables incompletas, omitiendo.")
    sys.exit(0)

print(f"[SUPERUSER] Buscando usuario con email={email}...")
u = User.objects.filter(email=email).first()

if u:
    u.set_password(password)
    u.is_superuser = True
    u.is_staff     = True
    u.is_active    = True
    u.role         = 'ADMIN'
    u.cedula       = u.cedula or cedula
    u.save()
    print(f"[SUPERUSER] ACTUALIZADO: {email} (ahora es ADMIN/staff/superuser)")
else:
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        cedula=cedula,
        role='ADMIN',
    )
    print(f"[SUPERUSER] CREADO: {email}")

sys.stdout.flush()
