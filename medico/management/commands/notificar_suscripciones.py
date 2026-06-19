"""
Envía correos a médicos cuya suscripción está por vencer o ya venció.
Se debe ejecutar diariamente (cron / Render Job):
    python manage.py notificar_suscripciones

Estrategia por plan:
- ANUAL/Trial: recordatorios a los 7, 3, 1 y 0 días antes (más oportunidades)
- MENSUAL: recordatorios a los 3, 1 y 0 días antes (más liviano, ya están acostumbrados)
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


def _html_recordatorio(medico, dias_aviso, renovar_url):
    """Construye el HTML del recordatorio según plan y días restantes."""
    plan = medico.plan_suscripcion or 'ANUAL'
    en_prueba = medico.en_periodo_prueba

    if en_prueba:
        suscripcion_tipo = "periodo de prueba GRATIS"
        opciones_pago = "$10/mes o $100/año (ahorras $20)"
    elif plan == 'MENSUAL':
        suscripcion_tipo = "suscripción mensual"
        opciones_pago = "$10/mes · O cambia a anual y ahorra $20 ($100/año)"
    else:
        suscripcion_tipo = "suscripción anual"
        opciones_pago = "$100/año"

    if dias_aviso == 0:
        tiempo = f"<strong>HOY ({medico.fecha_fin_suscripcion:%d/%m/%Y})</strong>"
        color_btn = "#198754"
    else:
        plural = "s" if dias_aviso != 1 else ""
        tiempo = (
            f"el <strong>{medico.fecha_fin_suscripcion:%d/%m/%Y}</strong> "
            f"(en {dias_aviso} día{plural})"
        )
        color_btn = "#0d6efd"

    return (
        f"<p>Hola Dr. {medico.usuario.first_name},</p>"
        f"<p>Tu {suscripcion_tipo} finaliza {tiempo}.</p>"
        f"<p>Renueva por <strong>{opciones_pago}</strong> para continuar sin interrupciones:</p>"
        f'<p><a href="{renovar_url}" style="background:{color_btn};color:#fff;'
        f'padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;">'
        f'Renovar suscripción</a></p>'
        f"<p style='color:#666;font-size:13px;margin-top:24px;'>"
        f"Si tienes dudas, escríbenos a contacto@vertexjd.com</p>"
    )


class Command(BaseCommand):
    help = (
        'Notifica a médicos sobre estado de suscripción. '
        'ANUAL/trial: 7,3,1,0 días antes. MENSUAL: 3,1,0 días antes.'
    )

    def handle(self, *args, **options):
        hoy = date.today()
        renovar_url = "https://sistema-salud.onrender.com/renovar-suscripcion/"

        # Mapa de días según plan: el médico recibe el aviso si encajan
        # con su plan_suscripcion (o si está en periodo de prueba).
        DIAS_ANUAL_O_TRIAL = (7, 3, 1, 0)
        DIAS_MENSUAL = (3, 1, 0)

        # Recorremos TODOS los días posibles y para cada uno notificamos
        # solo a los médicos cuyo plan corresponde
        for dias_aviso in (7, 3, 1, 0):
            objetivo = hoy + timedelta(days=dias_aviso)
            medicos = Medico.objects.filter(fecha_fin_suscripcion=objetivo)

            for m in medicos:
                # Decidir si este médico aplica para recibir aviso hoy
                if m.en_periodo_prueba or m.plan_suscripcion == 'ANUAL':
                    if dias_aviso not in DIAS_ANUAL_O_TRIAL:
                        continue
                elif m.plan_suscripcion == 'MENSUAL':
                    if dias_aviso not in DIAS_MENSUAL:
                        continue

                # Asunto según urgencia
                if dias_aviso == 0:
                    asunto = "⚠️ Tu suscripción VertexSalud vence HOY"
                else:
                    plural = "s" if dias_aviso != 1 else ""
                    asunto = f"VertexSalud: tu suscripción vence en {dias_aviso} día{plural}"

                html = _html_recordatorio(m, dias_aviso, renovar_url)
                if _enviar_correo(m.usuario.email, asunto, html):
                    plan_log = (
                        'TRIAL' if m.en_periodo_prueba
                        else (m.plan_suscripcion or 'ANUAL')
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"Notificado {m.usuario.email} ({plan_log}, vence en {dias_aviso}d)"
                    ))

        # Notificar a vencidos hace 1 día (acceso bloqueado)
        vencido_ayer = hoy - timedelta(days=1)
        for m in Medico.objects.filter(fecha_fin_suscripcion=vencido_ayer):
            html = (
                f"<p>Hola Dr. {m.usuario.first_name},</p>"
                f"<p>Tu suscripción venció ayer y tu acceso al sistema está bloqueado.</p>"
                f"<p>Renueva ahora para reactivar tu cuenta — $10/mes o $100/año:</p>"
                f'<p><a href="{renovar_url}" style="background:#dc3545;color:#fff;'
                f'padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;">'
                f'Reactivar cuenta</a></p>'
            )
            _enviar_correo(m.usuario.email, "Tu suscripción VertexSalud está vencida", html)

        self.stdout.write(self.style.SUCCESS("Proceso de notificaciones completado"))
