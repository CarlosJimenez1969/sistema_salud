from django.db import models
from django.conf import settings
from medico.models import Medico
from paciente.models import Paciente, Mascota

class Cita(models.Model):
    ESTADOS = [
        ('P', 'Pendiente'),
        ('E', 'En Espera'),
        ('A', 'Atendido'),
        ('C', 'Cancelado'),
    ]

    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='citas')
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='citas')
    # Solo se usa para citas veterinarias (el paciente es el dueño)
    mascota = models.ForeignKey(Mascota, on_delete=models.PROTECT, null=True, blank=True, related_name='citas')

    fecha = models.DateField()
    hora = models.TimeField()
    motivo = models.TextField(blank=True, help_text="Motivo de la consulta")

    estado = models.CharField(max_length=20, choices=ESTADOS, default='P')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ordenar por fecha y hora (las más próximas primero)
        ordering = ['fecha', 'hora']

    def __str__(self):
        return f"Cita: {self.paciente} con {self.medico} - {self.fecha} {self.hora}"