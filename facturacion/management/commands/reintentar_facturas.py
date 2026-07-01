"""Reintenta facturas SRI que quedaron en estado PENDIENTE por errores temporales
(fecha extemporánea, servicio SRI caído, etc.).

Diseñado para ejecutarse por cron cada 15 min: procesará todas las PENDIENTE
sin importar cuántos intentos previos hayan tenido. Alerta al admin si una
factura acumula demasiados intentos sin autorizarse.

Uso:
    python manage.py reintentar_facturas               # reintenta todas las PENDIENTE
    python manage.py reintentar_facturas --id 16       # reintenta solo la #16
    python manage.py reintentar_facturas --dry-run     # muestra qué haría sin ejecutar
    python manage.py reintentar_facturas --verbose     # más output para debugging
"""
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from facturacion.models import FacturaElectronica


# Después de este # de intentos sin éxito → email de aviso al admin
UMBRAL_ALERTA_INTENTOS = 24    # ~6 horas si el cron corre cada 15 min

# Después de este # → marcar como RECHAZADA definitiva (algo estructural está mal)
UMBRAL_RENDIRSE_INTENTOS = 288  # ~72 horas (3 días) si el cron corre cada 15 min


class Command(BaseCommand):
    help = 'Reintenta facturas SRI en estado PENDIENTE. Diseñado para cron cada 15 min.'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, default=None,
                            help='ID específico de la factura a reintentar.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo muestra qué facturas se reintentarían.')
        parser.add_argument('--verbose', action='store_true',
                            help='Output extendido.')

    def handle(self, *args, **options):
        from facturacion.services.sri import SriService

        qs = FacturaElectronica.objects.filter(estado='PENDIENTE').order_by(
            'ultimo_intento_sri', 'id',  # NULL first, luego más viejos
        )
        if options['id']:
            qs = qs.filter(id=options['id'])

        total = qs.count()
        if total == 0:
            if options['verbose']:
                self.stdout.write('Sin facturas PENDIENTE.')
            return

        self.stdout.write(f'[{timezone.now():%Y-%m-%d %H:%M}] Reintentando {total} factura(s) PENDIENTE...')

        if options['dry_run']:
            for f in qs:
                self.stdout.write(
                    f'  DRY #{f.id} {f.numero_secuencial} '
                    f'intentos={f.intentos_sri} ultimo={f.ultimo_intento_sri or "nunca"}'
                )
            return

        sri = SriService()
        exitosas = rechazadas = pendientes = errores = alertadas = rendidas = 0

        for factura in qs:
            self._reintentar_una(factura, sri, options['verbose'])

            # Contabilidad
            if factura.estado == 'AUTORIZADA':
                exitosas += 1
            elif factura.estado == 'RECHAZADA':
                rendidas += 1  # se rindió tras intentos máximos
            elif factura.estado == 'PENDIENTE':
                pendientes += 1
                if factura.intentos_sri == UMBRAL_ALERTA_INTENTOS:
                    self._alertar_admin_intentos(factura)
                    alertadas += 1
            else:
                errores += 1

        self.stdout.write(
            f'Resumen: {exitosas} OK · {pendientes} siguen PENDIENTE · '
            f'{rendidas} rendidas (RECHAZADA definitiva) · '
            f'{errores} errores · {alertadas} alertas nuevas'
        )

    def _reintentar_una(self, factura, sri, verbose):
        """Reintenta una factura. Actualiza intentos_sri y ultimo_intento_sri."""
        factura.intentos_sri += 1
        factura.ultimo_intento_sri = timezone.now()

        # Si ya llegó al máximo, marcarla RECHAZADA definitiva y avisar
        if factura.intentos_sri > UMBRAL_RENDIRSE_INTENTOS:
            factura.estado = 'RECHAZADA'
            factura.mensajes_sri = (
                f'[SISTEMA] Se agotaron {UMBRAL_RENDIRSE_INTENTOS} intentos '
                f'sin autorización. Revisar manualmente. '
                f'Último error SRI: {factura.mensajes_sri[:150]}'
            )
            factura.save()
            self._alertar_admin_rendida(factura)
            self.stdout.write(self.style.ERROR(
                f'  #{factura.id} → RENDIDA (>{UMBRAL_RENDIRSE_INTENTOS} intentos)'
            ))
            return

        try:
            # Regenerar clave_acceso con fecha actual (soluciona extemporánea)
            nueva_clave = sri.generar_clave_acceso(
                datetime.now(),
                factura.secuencial_numero,
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

            # procesar_factura ya llama a factura.save() al final
            # pero nuestros campos intentos_sri/ultimo_intento_sri se setearon antes;
            # los volvemos a guardar por si acaso
            factura.intentos_sri  # noqa: dummy read
            FacturaElectronica.objects.filter(id=factura.id).update(
                intentos_sri=factura.intentos_sri,
                ultimo_intento_sri=factura.ultimo_intento_sri,
            )

            if factura.estado == 'AUTORIZADA':
                self.stdout.write(self.style.SUCCESS(
                    f'  #{factura.id} → AUTORIZADA (intento {factura.intentos_sri})'
                ))
            elif verbose:
                self.stdout.write(
                    f'  #{factura.id} → {factura.estado} (intento {factura.intentos_sri}): '
                    f'{(factura.mensajes_sri or "-")[:80]}'
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'  #{factura.id} EXCEPCION: {type(e).__name__}: {e}'
            ))
            # Aseguramos que los contadores queden guardados aunque haya fallado
            FacturaElectronica.objects.filter(id=factura.id).update(
                intentos_sri=factura.intentos_sri,
                ultimo_intento_sri=factura.ultimo_intento_sri,
            )

    def _alertar_admin_intentos(self, factura):
        """Aviso al admin cuando la factura acumula UMBRAL_ALERTA_INTENTOS reintentos."""
        try:
            from facturacion.alerts import _enviar_email_admin
            html = (
                "<h3 style='color:#ff9800;'>⚠️ Factura SRI acumula reintentos</h3>"
                f"<p>La factura <strong>#{factura.id} ({factura.numero_secuencial})</strong> "
                f"lleva <strong>{factura.intentos_sri} intentos</strong> sin autorización.</p>"
                "<h4>Detalles:</h4>"
                "<ul>"
                f"<li><strong>Receptor:</strong> {factura.receptor_nombre} ({factura.receptor_email})</li>"
                f"<li><strong>Monto:</strong> ${factura.total}</li>"
                f"<li><strong>Último error SRI:</strong> {factura.mensajes_sri[:200]}</li>"
                f"<li><strong>Último intento:</strong> {factura.ultimo_intento_sri}</li>"
                "</ul>"
                "<p>El sistema seguirá reintentando cada 15 min hasta agotar "
                f"{UMBRAL_RENDIRSE_INTENTOS} intentos.</p>"
            )
            _enviar_email_admin(
                f"⚠️ VertexSalud — Factura #{factura.id} sigue sin autorizarse tras {factura.intentos_sri} intentos",
                html,
            )
        except Exception as e:
            print(f"[ALERT] No pude enviar aviso de umbral: {e}")

    def _alertar_admin_rendida(self, factura):
        """Aviso crítico cuando el sistema se rinde con una factura."""
        try:
            from facturacion.alerts import _enviar_email_admin
            html = (
                "<h3 style='color:#dc3545;'>🚨 Factura SRI marcada como RECHAZADA definitiva</h3>"
                f"<p>Tras {factura.intentos_sri} intentos sin éxito, el sistema abandonó "
                f"la factura <strong>#{factura.id} ({factura.numero_secuencial})</strong>.</p>"
                "<p><strong>Requiere intervención manual.</strong></p>"
                "<h4>Detalles:</h4>"
                "<ul>"
                f"<li><strong>Receptor:</strong> {factura.receptor_nombre}</li>"
                f"<li><strong>Monto:</strong> ${factura.total}</li>"
                f"<li><strong>Último error SRI:</strong> {factura.mensajes_sri[:300]}</li>"
                "</ul>"
                "<p>Acciones sugeridas:</p>"
                "<ol>"
                "<li>Revisar el mensaje SRI para entender el problema estructural</li>"
                "<li>Corregir en Django shell y reintentar manualmente: "
                f"<code>python manage.py reintentar_facturas --id {factura.id}</code></li>"
                "</ol>"
            )
            _enviar_email_admin(
                f"🚨 VertexSalud — Factura #{factura.id} RECHAZADA definitiva",
                html,
            )
        except Exception as e:
            print(f"[ALERT] No pude enviar aviso de rendición: {e}")
