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

    # Modalidad de atención (atributo de primera clase, no texto en observaciones)
    MODALIDADES = [
        ('PRESENCIAL', 'Presencial'),
        ('TELECONSULTA', 'Teleconsulta'),
        ('TELEINTERCONSULTA', 'Teleinterconsulta'),
        ('TELEMONITOREO', 'Telemonitoreo'),
    ]

    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='citas')
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='citas')
    # Solo se usa para citas veterinarias (el paciente es el dueño)
    mascota = models.ForeignKey(Mascota, on_delete=models.PROTECT, null=True, blank=True, related_name='citas')

    fecha = models.DateField()
    hora = models.TimeField()
    motivo = models.TextField(blank=True, help_text="Motivo de la consulta")

    estado = models.CharField(max_length=20, choices=ESTADOS, default='P')
    modalidad = models.CharField(
        max_length=20, choices=MODALIDADES, default='PRESENCIAL',
        help_text="Presencial o modalidad remota (telesalud)")
    creado_en = models.DateTimeField(auto_now_add=True)

    @property
    def es_remota(self):
        return self.modalidad != 'PRESENCIAL'

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


class SolicitudCita(models.Model):
    """Solicitud de cita generada desde la ficha pública del médico (sin login).
    El médico la revisa y luego la convierte en una Cita real eligiendo hora."""

    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('contactada', 'Contactada'),
        ('agendada', 'Agendada'),
        ('descartada', 'Descartada'),
    ]

    medico = models.ForeignKey(
        Medico, on_delete=models.CASCADE, related_name='solicitudes_cita')
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30)
    motivo = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    origen = models.CharField(max_length=40, default='ficha_publica')
    # Cita real generada al agendar (para trazabilidad)
    cita = models.ForeignKey(
        'Cita', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='solicitud_origen')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Solicitud de cita'
        verbose_name_plural = 'Solicitudes de cita'

    def __str__(self):
        return f"{self.nombre} → Dr. {self.medico.usuario.last_name} ({self.get_estado_display()})"

    @property
    def telefono_normalizado(self):
        tel = (self.telefono or '').strip().replace(' ', '').replace('-', '').replace('+', '')
        if not tel or not tel.replace('.', '').isdigit():
            return None
        if tel.startswith('593'):
            return tel
        if tel.startswith('0'):
            return '593' + tel[1:]
        return '593' + tel  # asumir Ecuador

    @property
    def whatsapp_link(self):
        numero = self.telefono_normalizado
        if not numero:
            return None
        from urllib.parse import quote
        mensaje = (
            f"Hola {self.nombre}, le contactamos de VertexSalud respecto a su "
            f"solicitud de cita. ¿Coordinamos día y hora?"
        )
        return f"https://wa.me/{numero}?text={quote(mensaje)}"