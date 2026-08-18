from django.contrib import admin

from .models import TeleconsultaSesion, ConsentimientoTelesalud, EventoAuditoria


@admin.register(TeleconsultaSesion)
class TeleconsultaSesionAdmin(admin.ModelAdmin):
    list_display = ('sala_id', 'estado', 'proveedor', 'inicio', 'fin', 'creado')
    list_filter = ('estado', 'proveedor')
    search_fields = ('sala_id', 'cita__paciente__usuario__email')
    readonly_fields = ('creado', 'actualizado')


@admin.register(ConsentimientoTelesalud)
class ConsentimientoTelesaludAdmin(admin.ModelAdmin):
    list_display = ('version_documento', 'aceptado', 'aceptado_por', 'aceptado_en', 'revocado')
    list_filter = ('aceptado', 'aceptado_por', 'revocado', 'version_documento')
    readonly_fields = ('hash_documento', 'aceptado_en', 'ip', 'user_agent', 'creado')


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'accion', 'recurso', 'ip')
    list_filter = ('accion',)
    search_fields = ('actor', 'accion', 'recurso')
    readonly_fields = ('actor', 'accion', 'recurso', 'sesion', 'ip', 'detalle', 'timestamp')

    def has_add_permission(self, request):
        return False  # append-only: no se crean/edian a mano

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
