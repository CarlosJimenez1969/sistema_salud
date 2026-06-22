"""
Envía correos a médicos cuya suscripción está por vencer o ya venció.
Se debe ejecutar diariamente (cron / Render Job):
    python manage.py notificar_suscripciones
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
import requests as http_requests
from medico.models import Medico


def _enviar_correo(email, asunto, html):
    if not settings.RESEND_API_KEY:
        print(f"[NOTIF] RESEND_API_KEY no configurado, no se envió a {email}")
        return False
    try:
        resp = http_requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.RESEND_FROM,
                "to": [email],
                "subject": asunto,
                "html": html,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[NOTIF ERROR] {email}: {e}")
        return False


class Command(BaseCommand):
    help = 'Notifica a médicos sobre estado de suscripción (faltan 7, 3, 1 días o vencida)'

    def handle(self, *args, **options):
        hoy = date.today()
        renovar_url = "https://sistema-salud.onrender.com/renovar-suscripcion/"

        # Días específicos a notificar (antes de vencer + el día que vence)
        for dias_aviso in (7, 3, 1, 0):
            objetivo = hoy + timedelta(days=dias_aviso)
            medicos = Medico.objects.filter(fecha_fin_suscripcion=objetivo)
            for m in medicos:
                if dias_aviso == 0:
                    asunto = "⚠️ Tu suscripción VertexSalud vence HOY"
                    html = (
                        f"<p>Hola Dr. {m.usuario.first_name},</p>"
                        f"<p>Tu {'periodo de prueba' if m.en_periodo_prueba else 'suscripción'} "
                        f"finaliza <strong>HOY ({m.fecha_fin_suscripcion:%d/%m/%Y})</strong>.</p>"
                        f"<p>Para no perder el acceso al sistema, renueva por $50/año:</p>"
                        f'<p><a href="{renovar_url}" style="background:#198754;color:#fff;padding:10px 20px;text-decoration:none;border-radius:5px;">Renovar ahora</a></p>'
                    )
                else:
                    asunto = f"VertexSalud: tu suscripción vence en {dias_aviso} día(s)"
                    html = (
                        f"<p>Hola Dr. {m.usuario.first_name},</p>"
                        f"<p>Te recordamos que tu "
                        f"{'periodo de prueba GRATIS' if m.en_periodo_prueba else 'suscripción'} "
                        f"finaliza el <strong>{m.fecha_fin_suscripcion:%d/%m/%Y}</strong> "
                        f"(en {dias_aviso} día{'s' if dias_aviso != 1 else ''}).</p>"
                        f"<p>Renueva por $50/año para continuar usando el sistema sin interrupciones:</p>"
                        f'<p><a href="{renovar_url}" style="background:#0d6efd;color:#fff;padding:10px 20px;text-decoration:none;border-radius:5px;">Renovar suscripción</a></p>'
                    )
                if _enviar_correo(m.usuario.email, asunto, html):
                    self.stdout.write(self.style.SUCCESS(f"Notificado {m.usuario.email} (vence en {dias_aviso}d)"))

        # Notificar a vencidos hace 1 día
        vencido_ayer = hoy - timedelta(days=1)
        for m in Medico.objects.filter(fecha_fin_suscripcion=vencido_ayer):
            html = (
                f"<p>Hola Dr. {m.usuario.first_name},</p>"
                f"<p>Tu suscripción venció ayer y tu acceso al sistema está bloqueado.</p>"
                f"<p>Renueva ahora para reactivar tu cuenta:</p>"
                f'<p><a href="{renovar_url}" style="background:#dc3545;color:#fff;padding:10px 20px;text-decoration:none;border-radius:5px;">Reactivar cuenta</a></p>'
            )
            _enviar_correo(m.usuario.email, "Tu suscripción VertexSalud está vencida", html)

        self.stdout.write(self.style.SUCCESS("Proceso de notificaciones completado"))
