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

    @property
    def telefono_normalizado(self):
        """Devuelve el teléfono en formato 593XXXXXXXXX (sin + ni espacios)."""
        tel = (self.paciente.telefono or '').strip().replace(' ', '').replace('-', '').replace('+', '')
        if not tel or not tel.replace('.', '').isdigit():
            return None
        if tel.startswith('593'):
            return tel
        if tel.startswith('0'):
            return '593' + tel[1:]
        return '593' + tel  # asumir Ecuador

    @property
    def whatsapp_link(self):
        """Genera link wa.me con mensaje de recordatorio pre-escrito."""
        numero = self.telefono_normalizado
        if not numero:
            return None

        from urllib.parse import quote
        nombre_paciente = self.paciente.usuario.first_name or "estimado/a"
        apellido_medico = self.medico.usuario.last_name
        fecha_str = self.fecha.strftime('%d/%m/%Y')
        hora_str  = self.hora.strftime('%H:%M')

        if self.mascota:
            mensaje = (
                f"Hola {nombre_paciente}, le recordamos la cita de {self.mascota.nombre} "
                f"con el Dr. {apellido_medico} el {fecha_str} a las {hora_str}. "
                f"— VertexSalud"
            )
        else:
            mensaje = (
                f"Hola {nombre_paciente}, le recordamos su cita "
                f"con el Dr. {apellido_medico} el {fecha_str} a las {hora_str}. "
                f"— VertexSalud"
            )

        return f"https://wa.me/{numero}?text={quote(mensaje)}"