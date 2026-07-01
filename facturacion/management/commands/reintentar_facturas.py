"""Reintenta facturas SRI que quedaron en estado PENDIENTE por errores temporales
(fecha extemporánea, servicio SRI caído, etc.).

Uso:
    python manage.py reintentar_facturas               # reintenta todas las PENDIENTE
    python manage.py reintentar_facturas --id 16       # reintenta solo la #16
    python manage.py reintentar_facturas --dry-run     # muestra qué haría sin ejecutar

Al reintentar:
  1. Regenera clave_acceso con la fecha actual (soluciona el problema de fecha
     extemporánea cuando la factura original se emitió tarde en la noche Ecuador).
  2. Regenera el XML con la nueva fecha.
  3. Firma el XML nuevo con el cert SRI.
  4. Envía al SRI y actualiza el estado.
"""
import random
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from facturacion.models import FacturaElectronica


class Command(BaseCommand):
    help = 'Reintenta facturas SRI en estado PENDIENTE por errores temporales.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            type=int,
            default=None,
            help='ID específico de la factura a reintentar. Si se omite, reintenta todas las PENDIENTE.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué facturas se reintentarían, sin ejecutar.',
        )

    def handle(self, *args, **options):
        from facturacion.services.sri import SriService

        qs = FacturaElectronica.objects.filter(estado='PENDIENTE').order_by('id')
        if options['id']:
            qs = qs.filter(id=options['id'])

        if not qs.exists():
            self.stdout.write(self.style.SUCCESS('No hay facturas PENDIENTE para reintentar.'))
            return

        self.stdout.write(f'Facturas a reintentar: {qs.count()}')
        for f in qs:
            self.stdout.write(
                f'  #{f.id} {f.numero_secuencial} '
                f'(mensajes: {(f.mensajes_sri or "-")[:80]})'
            )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n[DRY-RUN] No se ejecutó nada.'))
            return

        sri = SriService()
        exitosas = 0
        rechazadas = 0
        pendientes = 0
        errores = 0

        for factura in qs:
            self.stdout.write(f'\n>>> Reintentando #{factura.id} {factura.numero_secuencial}...')
            try:
                # Regenerar clave_acceso con fecha actual (soluciona extemporánea)
                nueva_clave = sri.generar_clave_acceso(
                    datetime.now(),
                    factura.secuencial_numero,
                )
                if nueva_clave != factura.clave_acceso:
                    self.stdout.write(
                        f'    clave anterior: {factura.clave_acceso}'
                    )
                    self.stdout.write(
                        f'    clave nueva:    {nueva_clave}'
                    )
                    factura.clave_acceso = nueva_clave

                # Limpiar campos que se regenerarán
                factura.xml_sin_firma = ''
                factura.xml_firmado = ''
                factura.mensajes_sri = ''
                factura.respuesta_sri = None
                factura.numero_autorizacion = ''
                factura.fecha_autorizacion = None
                factura.fecha_envio = None

                # Procesar (genera XML → firma → envía → autoriza)
                sri.procesar_factura(factura)

                if factura.estado == 'AUTORIZADA':
                    exitosas += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'    OK autorizada: {factura.numero_autorizacion}'
                    ))
                elif factura.estado == 'PENDIENTE':
                    pendientes += 1
                    self.stdout.write(self.style.WARNING(
                        f'    Sigue PENDIENTE: {factura.mensajes_sri[:100]}'
                    ))
                elif factura.estado == 'RECHAZADA':
                    rechazadas += 1
                    self.stdout.write(self.style.ERROR(
                        f'    RECHAZADA definitiva: {factura.mensajes_sri[:100]}'
                    ))
                else:
                    errores += 1
                    self.stdout.write(self.style.ERROR(
                        f'    ERROR estado={factura.estado}: {factura.mensajes_sri[:100]}'
                    ))
            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR(f'    EXCEPCION: {type(e).__name__}: {e}'))

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'Resumen: {exitosas} autorizadas · {pendientes} siguen pendientes · '
                          f'{rechazadas} rechazadas · {errores} errores')
        self.stdout.write('=' * 60)
