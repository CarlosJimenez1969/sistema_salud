from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Definimos los roles posibles
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        MEDICO = "MEDICO", "Médico"
        PACIENTE = "PACIENTE", "Paciente"
        SECRETARIA = "SECRETARIA", "Secretaria"

    base_role = Role.ADMIN
    
    # Campos adicionales que todo usuario debe tener
    email = models.EmailField(unique=True) # Usaremos el email para loguearse, no el usuario
    cedula = models.CharField(max_length=15, unique=True, null=True, blank=True)
    role = models.CharField(max_length=50, choices=Role.choices, default=base_role)
    
    # Campo para saber si un médico ya pagó (para tu requerimiento de pagos)
    pago_realizado = models.BooleanField(default=False)

    # Configuración para usar email en lugar de username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'cedula']

    def __str__(self):
        return f"{self.email} ({self.role})"
