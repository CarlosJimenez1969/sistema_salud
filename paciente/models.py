from django.db import models
from django.conf import settings
from django.utils import timezone

class Paciente(models.Model):
    SEXO_CHOICES = [('M', 'Masculino'), ('F', 'Femenino')]

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_paciente')
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, default='M')
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)

    # Datos médicos básicos para la historia
    tipo_sangre = models.CharField(max_length=10, blank=True)
    alergias = models.TextField(blank=True, help_text="Alergias conocidas")
    enfermedades_cronicas = models.TextField(blank=True, help_text="Enfermedades preexistentes")

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.now().date()
        return hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )

    def __str__(self):
        # Si tiene nombre o apellido, muéstralos
        if self.usuario.first_name or self.usuario.last_name:
            return f"{self.usuario.last_name} {self.usuario.first_name}"
        # Si no, muestra el email para que sepamos quién es
        return self.usuario.email