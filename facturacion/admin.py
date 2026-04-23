from django.contrib import admin
from .models import FacturaElectronica, SecuencialFactura


@admin.register(FacturaElectronica)
class FacturaElectronicaAdmin(admin.ModelAdmin):
    list_display = [
        'numero_secuencial', 'receptor_nombre', 'receptor_identificacion',
        'total', 'estado', 'fecha_emision', 'numero_autorizacion',
    ]
    list_filter = ['estado', 'fecha_emision']
    search_fields = ['receptor_nombre', 'receptor_identificacion', 'clave_acceso', 'numero_autorizacion']
    readonly_fields = [
        'clave_acceso', 'numero_secuencial', 'secuencial_numero',
        'xml_sin_firma', 'xml_firmado', 'respuesta_sri',
        'fecha_emision', 'fecha_envio', 'numero_autorizacion', 'fecha_autorizacion',
    ]
    fieldsets = (
        ('Identificación', {
            'fields': ('numero_secuencial', 'clave_acceso', 'estado'),
        }),
        ('Receptor', {
            'fields': ('receptor_tipo_id', 'receptor_identificacion', 'receptor_nombre', 'receptor_email', 'receptor_direccion'),
        }),
        ('Montos', {
            'fields': ('subtotal', 'iva_porcentaje', 'iva_valor', 'total', 'descripcion'),
        }),
        ('Respuesta SRI', {
            'fields': ('numero_autorizacion', 'fecha_autorizacion', 'mensajes_sri', 'respuesta_sri'),
            'classes': ('collapse',),
        }),
        ('XML', {
            'fields': ('xml_sin_firma', 'xml_firmado'),
            'classes': ('collapse',),
        }),
    )


@admin.register(SecuencialFactura)
class SecuencialFacturaAdmin(admin.ModelAdmin):
    list_display = ['establecimiento', 'punto_emision', 'ultimo_secuencial']
