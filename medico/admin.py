from django.contrib import admin
from .models import Especialidad, Medico, Pais, Ciudad


class CiudadInline(admin.TabularInline):
    model = Ciudad
    extra = 3


@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display  = ['nombre']
    search_fields = ['nombre']
    inlines       = [CiudadInline]


@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'pais']
    list_filter   = ['pais']
    search_fields = ['nombre']


admin.site.register(Especialidad)
admin.site.register(Medico)
