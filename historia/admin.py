from django.contrib import admin
from .models import HistoriaClinica, ImagenHistoria

# Esto permite subir las imágenes DENTRO de la misma pantalla de la historia
class ImagenInline(admin.TabularInline):
    model = ImagenHistoria
    extra = 1

class HistoriaAdmin(admin.ModelAdmin):
    inlines = [ImagenInline]
    list_display = ('paciente', 'medico', 'fecha_atencion', 'diagnostico')
    search_fields = ('paciente__usuario__last_name', 'paciente__usuario__cedula')

admin.site.register(HistoriaClinica, HistoriaAdmin)