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


class Mascota(models.Model):
    ESPECIES = [
        ('PERRO',   'Perro'),
        ('GATO',    'Gato'),
        ('AVE',     'Ave'),
        ('CONEJO',  'Conejo'),
        ('ROEDOR',  'Roedor (cuy, hámster, etc.)'),
        ('REPTIL',  'Reptil'),
        ('PEZ',     'Pez'),
        ('OTRO',    'Otro'),
    ]
    SEXO_MASCOTA = [('M', 'Macho'), ('H', 'Hembra')]

    propietario      = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='mascotas')
    nombre           = models.CharField(max_length=80)
    especie          = models.CharField(max_length=10, choices=ESPECIES)
    raza             = models.CharField(max_length=80, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo             = models.CharField(max_length=1, choices=SEXO_MASCOTA, blank=True)
    color            = models.CharField(max_length=50, blank=True)
    peso             = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Kg")
    esterilizado     = models.BooleanField(default=False)
    chip_id          = models.CharField(max_length=50, blank=True, help_text="Microchip / ID de identificación")
    foto             = models.ImageField(upload_to='mascotas/', null=True, blank=True)
    alergias         = models.TextField(blank=True)
    enfermedades_cronicas = models.TextField(blank=True)
    notas            = models.TextField(blank=True)
    activo           = models.BooleanField(default=True)
    creado           = models.DateTimeField(auto_now_add=True)

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.now().date()
        years = hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
        if years >= 1:
            return f"{years} año{'s' if years != 1 else ''}"
        meses = (hoy.year - self.fecha_nacimiento.year) * 12 + (hoy.month - self.fecha_nacimiento.month)
        if hoy.day < self.fecha_nacimiento.day:
            meses -= 1
        return f"{max(meses, 0)} meses"

    def __str__(self):
        return f"{self.nombre} ({self.get_especie_display()})"