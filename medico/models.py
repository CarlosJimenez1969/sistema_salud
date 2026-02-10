from django.db import models
from django.conf import settings # Para conectar con nuestro usuario

# Modelo para las Especialidades (Cardiología, Pediatría, etc.)
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
    
    # Horario de atención (Simplificado para empezar)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"Dr. {self.usuario.last_name} - {self.especialidad}"