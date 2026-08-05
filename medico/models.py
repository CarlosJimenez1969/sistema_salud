from django.db import models
from django.conf import settings


class Pais(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Países"
        ordering = ['nombre']


class Ciudad(models.Model):
    nombre = models.CharField(max_length=100)
    pais   = models.ForeignKey(Pais, on_delete=models.CASCADE, related_name='ciudades')

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ['nombre']
        unique_together = ('nombre', 'pais')


class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    
    # Esto es para que en el panel admin aparezca el nombre y no "Object 1"
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name_plural = "Especialidades"

# Modelo para el perfil profesional del médico
class Medico(models.Model):
    # Relación 1 a 1: Un usuario TIENE UN perfil de médico
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_medico')
    
    # Relación: Un médico pertenece a una especialidad
    especialidad = models.ForeignKey(Especialidad, on_delete=models.SET_NULL, null=True)
    
    # Datos profesionales
    registro_senescyt = models.CharField(max_length=50, blank=True, help_text="Número de registro SENESCYT (legacy)")
    registro_msp = models.CharField(
        max_length=20, null=True, blank=True, unique=True,
        help_text="Número de Registro Profesional emitido por el MSP",
    )
    telefono_consultorio = models.CharField(max_length=20, blank=True)
    direccion_consultorio = models.TextField(blank=True)
    
    # Costo de la cita (útil para el pago posterior)
    precio_consulta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Ubicación del consultorio
    pais = models.CharField(max_length=100, blank=True, default='Ecuador')
    ciudad = models.CharField(max_length=100, blank=True)
    SECTORES = [
        ('', '-- Seleccionar --'),
        ('NORTE', 'Norte'),
        ('CENTRO', 'Centro'),
        ('SUR', 'Sur'),
        ('VALLES', 'Valles'),
        ('OTRO', 'Otro'),
    ]
    sector = models.CharField(max_length=10, choices=SECTORES, blank=True)

    # Horario de atención (Simplificado para empezar)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    intervalo_minutos = models.PositiveIntegerField(default=30, help_text="Duración de cada cita en minutos")

    # ── Suscripción / Periodo de prueba ───────────────────────────────────────
    fecha_inicio_suscripcion = models.DateField(null=True, blank=True)
    fecha_fin_suscripcion    = models.DateField(null=True, blank=True, help_text="Fecha en la que vence la suscripción (prueba o pagada)")
    en_periodo_prueba        = models.BooleanField(default=True, help_text="True = trial gratis; False = suscripción pagada")

    @property
    def dias_restantes_suscripcion(self):
        if not self.fecha_fin_suscripcion:
            return 0
        from datetime import date
        delta = (self.fecha_fin_suscripcion - date.today()).days
        return max(delta, 0)

    @property
    def suscripcion_activa(self):
        if not self.fecha_fin_suscripcion:
            return False
        from datetime import date
        return date.today() <= self.fecha_fin_suscripcion

    @property
    def suscripcion_por_vencer(self):
        """True si quedan 7 días o menos."""
        return self.suscripcion_activa and self.dias_restantes_suscripcion <= 7

    def __str__(self):
        return f"Dr. {self.usuario.last_name} - {self.especialidad}"
    
class Secretaria(models.Model):
    # Relación uno a uno con el usuario de Django
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='perfil_secretaria'
    )
    # Relación con el médico al que asiste (Muchos a uno)
    medico = models.ForeignKey(
        'Medico', 
        on_delete=models.CASCADE, 
        related_name='mis_secretarias'
    )
    telefono = models.CharField(max_length=20, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Secretaria: {self.usuario.get_full_name()} (Asiste al Dr. {self.medico.usuario.last_name})"

    class Meta:
        verbose_name = "Secretaria"
        verbose_name_plural = "Secretarias"


class FichaPublica(models.Model):
    """Página pública (sin login) del médico para que un paciente lo encuentre
    en Google y solicite una cita. OneToOne con el perfil de Médico."""

    medico = models.OneToOneField(
        'Medico', on_delete=models.CASCADE, related_name='ficha')
    # Slug único para la URL pública /p/<slug>/
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    publicada = models.BooleanField(
        default=False, help_text="Si está marcada, la ficha es visible en /p/<slug>/")

    titulo_profesional = models.CharField(
        "título o especialidad", max_length=120, blank=True)
    descripcion = models.TextField(blank=True)
    servicios = models.TextField(blank=True, help_text="Uno por línea")
    ciudad = models.CharField(max_length=100, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    mapa_url = models.URLField(
        "enlace de Google Maps", blank=True,
        help_text="Se arma automáticamente al marcar tu ubicación en el mapa.")
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    horarios = models.TextField(blank=True, help_text="Uno por línea")
    precio_consulta = models.DecimalField(
        "valor de la consulta", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Opcional. Si lo dejas vacío, no se muestra el precio en tu página.")

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ficha pública"
        verbose_name_plural = "Fichas públicas"

    def __str__(self):
        return f"Ficha pública de {self.medico}"

    def _base_slug(self):
        from django.utils.text import slugify
        u = self.medico.usuario
        nombre = (u.get_full_name() or getattr(u, 'username', '') or 'medico').strip()
        esp = self.medico.especialidad.nombre if self.medico.especialidad else ''
        base = slugify(f"dr-{nombre}-{esp}") or f"medico-{self.medico_id}"
        return base[:120]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = self._base_slug()
            slug, i = base, 1
            while FichaPublica.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def lista_servicios(self):
        return [s.strip() for s in self.servicios.splitlines() if s.strip()]

    def lista_horarios(self):
        return [h.strip() for h in self.horarios.splitlines() if h.strip()]