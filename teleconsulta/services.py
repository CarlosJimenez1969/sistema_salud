"""Servicios/ayudas del módulo de telesalud."""
from datetime import timedelta

from django.utils import timezone

from .models import TeleconsultaSesion, EventoAuditoria


# Texto del consentimiento informado de telesalud (versionado).
# Distinto del consentimiento general de atención: explica limitaciones del acto
# remoto, alternativas presenciales, riesgos de conectividad y tratamiento de datos.
CONSENT_VERSION = 'v1'
CONSENT_TEXT = """CONSENTIMIENTO INFORMADO PARA ATENCIÓN POR TELESALUD

Declaro que se me ha explicado y comprendo lo siguiente:

1. La teleconsulta es un acto médico realizado a distancia mediante video. No
   reemplaza en todos los casos a la consulta presencial; el profesional puede
   indicar que mi caso requiere atención presencial.

2. Limitaciones: el examen físico es limitado. Si el profesional considera que
   necesita evaluarme en persona, la teleconsulta puede suspenderse y derivarse a
   atención presencial.

3. Alternativa presencial: puedo optar por una atención presencial en lugar de la
   teleconsulta en cualquier momento.

4. Riesgos de conectividad: la calidad de la llamada depende de mi conexión a
   internet. Una falla técnica puede interrumpir la atención; en ese caso se
   reagenda sin costo adicional.

5. Tratamiento de datos (LOPDP): mis datos de salud son de categoría sensible y
   serán tratados de forma confidencial, con las medidas de seguridad
   correspondientes, únicamente para mi atención en salud. Puedo ejercer mis
   derechos de acceso, rectificación, eliminación, portabilidad y oposición.

6. La atención quedará registrada en mi historia clínica única, identificada como
   modalidad remota, con el mismo valor que una consulta presencial.

7. Puedo REVOCAR este consentimiento en cualquier momento.

Al aceptar, confirmo que soy la persona que solicita la atención (o su
representante legal debidamente identificado) y que otorgo mi consentimiento para
ser atendido/a por telesalud."""


def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def sesion_para_cita(cita, ventana_horas=6):
    """Obtiene o crea la sesión de teleconsulta de una cita remota.
    El token caduca a las `ventana_horas` de la fecha/hora de la cita."""
    sesion, creada = TeleconsultaSesion.objects.get_or_create(cita=cita)
    if creada or not sesion.token_expira:
        from datetime import datetime
        inicio_cita = timezone.make_aware(datetime.combine(cita.fecha, cita.hora)) \
            if timezone.is_naive(datetime.combine(cita.fecha, cita.hora)) \
            else datetime.combine(cita.fecha, cita.hora)
        sesion.token_expira = inicio_cita + timedelta(hours=ventana_horas)
        sesion.save(update_fields=['token_expira'])
    return sesion


def jitsi_domain():
    # Fase 1: servidor público de Jitsi. En producción se auto-hospeda en el VPS
    # para soberanía de datos (Norma de Telesalud / LOPDP).
    return 'meet.jit.si'
