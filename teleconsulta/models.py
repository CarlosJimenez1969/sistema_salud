"""Modelos del módulo de Telesalud (Fase 1 MVP).

Diseño alineado con la Norma Técnica de Telesalud (Ecuador) y la LOPDP:
- La teleconsulta NO es un expediente aparte: se ancla a la Cita y a la Historia
  Clínica del paciente (misma HC única), marcada como modalidad remota.
- Consentimiento electrónico versionado, con sello de tiempo/IP/dispositivo y
  hash del documento aceptado, vinculado a paciente + cita.
- Auditoría append-only: quién hizo qué, cuándo y desde dónde.
"""
import hashlib
import uuid

from django.db import models
from django.utils import timezone


def _nuevo_sala_id():
    return 'vsalud-' + uuid.uuid4().hex[:20]


def _nuevo_token():
    # Token largo para el enlace del paciente (gate de acceso a la sala)
    return uuid.uuid4().hex + uuid.uuid4().hex[:24]


class TeleconsultaSesion(models.Model):
    ESTADOS = [
        ('PROGRAMADA', 'Programada'),
        ('CONSENTIMIENTO', 'Consentimiento pendiente'),
        ('PRECHECK', 'Verificación técnica'),
        ('SALA_ESPERA', 'En sala de espera'),
        ('EN_CURSO', 'En curso'),
        ('FINALIZADA', 'Finalizada'),
        ('DERIVADA', 'Derivada a presencial/emergencia'),
        ('FALLIDA', 'Falla técnica'),
        ('CANCELADA', 'Cancelada'),
    ]

    DERIVACION_TIPOS = [
        ('PRESENCIAL', 'Atención presencial'),
        ('EMERGENCIA', 'Emergencia (ECU-911)'),
    ]

    cita = models.OneToOneField(
        'citas.Cita', on_delete=models.CASCADE, related_name='teleconsulta')
    sala_id = models.CharField(max_length=64, unique=True, default=_nuevo_sala_id)
    proveedor = models.CharField(max_length=20, default='jitsi')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PROGRAMADA')

    # Enlace del paciente: token por sesión con expiración (no estático reutilizable).
    # Permite reingreso durante la ventana de la sesión; caduca al terminar.
    token = models.CharField(max_length=96, unique=True, default=_nuevo_token)
    token_expira = models.DateTimeField(null=True, blank=True)

    # Control de sala de espera (el médico admite; nadie entra sin admisión)
    paciente_en_espera = models.BooleanField(default=False)
    paciente_admitido = models.BooleanField(default=False)

    inicio = models.DateTimeField(null=True, blank=True)
    fin = models.DateTimeField(null=True, blank=True)
    ubicacion_declarada_paciente = models.CharField(max_length=200, blank=True)

    # Escalamiento / derivación (seguridad clínica)
    derivacion_tipo = models.CharField(max_length=20, choices=DERIVACION_TIPOS, blank=True)
    derivacion_motivo = models.TextField(blank=True)
    derivada_en = models.DateTimeField(null=True, blank=True)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sesión de teleconsulta'
        verbose_name_plural = 'Sesiones de teleconsulta'

    def __str__(self):
        return f"Teleconsulta {self.sala_id} ({self.get_estado_display()})"

    @property
    def duracion_efectiva(self):
        if self.inicio and self.fin:
            return self.fin - self.inicio
        return None

    @property
    def token_vigente(self):
        if not self.token_expira:
            return True
        return timezone.now() <= self.token_expira

    @property
    def consentimiento_aceptado(self):
        return self.consentimientos.filter(aceptado=True).exists()


class ConsentimientoTelesalud(models.Model):
    """Consentimiento informado ELECTRÓNICO específico de telesalud.
    Versionado, con sello de tiempo/IP/dispositivo y hash del documento.
    Se adjunta a la historia clínica (no es una tabla suelta): se vincula a la
    sesión → cita → paciente, y su texto/hash queda disponible para la HC."""

    ACEPTADO_POR = [
        ('PACIENTE', 'El propio paciente'),
        ('REPRESENTANTE', 'Representante legal / tutor'),
    ]

    sesion = models.ForeignKey(
        TeleconsultaSesion, on_delete=models.CASCADE, related_name='consentimientos')
    paciente = models.ForeignKey(
        'paciente.Paciente', on_delete=models.CASCADE,
        related_name='consentimientos_telesalud', null=True, blank=True)

    tipo = models.CharField(max_length=30, default='TELESALUD')
    version_documento = models.CharField(max_length=10, default='v1')
    texto_documento = models.TextField(help_text="Texto exacto que el paciente aceptó")

    aceptado = models.BooleanField(default=False)
    aceptado_en = models.DateTimeField(null=True, blank=True)
    aceptado_por = models.CharField(max_length=20, choices=ACEPTADO_POR, default='PACIENTE')

    # Si es menor de edad o incapaz: datos del representante + parentesco
    representante_nombre = models.CharField(max_length=150, blank=True)
    representante_cedula = models.CharField(max_length=20, blank=True)
    representante_parentesco = models.CharField(max_length=50, blank=True)

    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    hash_documento = models.CharField(max_length=64, blank=True)

    # Revocable en cualquier momento (LOPDP)
    revocado = models.BooleanField(default=False)
    revocado_en = models.DateTimeField(null=True, blank=True)

    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Consentimiento de telesalud'
        verbose_name_plural = 'Consentimientos de telesalud'
        ordering = ['-creado']

    def __str__(self):
        estado = 'aceptado' if self.aceptado else 'pendiente'
        return f"Consentimiento {self.version_documento} ({estado})"

    def sellar(self, ip=None, user_agent=''):
        """Marca el consentimiento como aceptado y calcula el hash del acto."""
        self.aceptado = True
        self.aceptado_en = timezone.now()
        self.ip = ip
        self.user_agent = user_agent or ''
        base = (
            f"{self.texto_documento}|{self.version_documento}|"
            f"{self.aceptado_por}|{self.aceptado_en.isoformat()}|{ip}"
        )
        self.hash_documento = hashlib.sha256(base.encode('utf-8')).hexdigest()
        self.save()


class EventoAuditoria(models.Model):
    """Log inmutable (append-only) de accesos y acciones sobre la teleconsulta.
    Quién, qué, cuándo y desde dónde. Exportable para auditoría."""

    actor = models.CharField(max_length=150, help_text="usuario o paciente:token")
    accion = models.CharField(max_length=80)
    recurso = models.CharField(max_length=160, blank=True)
    sesion = models.ForeignKey(
        TeleconsultaSesion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='auditoria')
    ip = models.GenericIPAddressField(null=True, blank=True)
    detalle = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento de auditoría'
        verbose_name_plural = 'Eventos de auditoría'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.actor} · {self.accion}"

    @staticmethod
    def registrar(actor, accion, recurso='', sesion=None, ip=None, **detalle):
        return EventoAuditoria.objects.create(
            actor=actor, accion=accion, recurso=recurso,
            sesion=sesion, ip=ip, detalle=detalle or {})
