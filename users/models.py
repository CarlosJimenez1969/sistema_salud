from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        MEDICO = "MEDICO", "Médico"
        PACIENTE = "PACIENTE", "Paciente"
        SECRETARIA = "SECRETARIA", "Secretaria"

    base_role = Role.PACIENTE
    email = models.EmailField(unique=True)
    cedula = models.CharField(max_length=15, unique=True, null=True, blank=True)
    role = models.CharField(max_length=50, choices=Role.choices, default=base_role)
    pago_realizado = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'cedula']

    def __str__(self):
        return f"{self.email} ({self.role})"