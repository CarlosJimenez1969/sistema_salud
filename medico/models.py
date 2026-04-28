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
    registro_senescyt = models.CharField(max_length=50, blank=True, help_text="Número de registro profesional")
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