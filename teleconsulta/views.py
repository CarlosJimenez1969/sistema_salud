"""Vistas del módulo de telesalud (Fase 1 MVP).

Flujo del paciente (por token, sin login):
  entrada → consentimiento → precheck → sala de espera → video
Flujo del médico (con login):
  panel/sala → admitir → video + panel clínico → finalizar
Señalización: por polling (Fase 1). WebSocket queda para Fase 2.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from citas.models import Cita
from .models import TeleconsultaSesion, ConsentimientoTelesalud, EventoAuditoria
from .services import (
    CONSENT_TEXT, CONSENT_VERSION, get_client_ip, sesion_para_cita, jitsi_domain,
)


# ─────────────────────────── Helpers ───────────────────────────
def _medico_del_usuario(request):
    medico = getattr(request.user, 'perfil_medico', None)
    if medico:
        return medico
    sec = getattr(request.user, 'perfil_secretaria', None)
    return sec.medico if sec else None


def _sesion_del_medico(request, sesion_id):
    medico = _medico_del_usuario(request)
    if not medico:
        return None, None
    sesion = get_object_or_404(TeleconsultaSesion, id=sesion_id)
    if sesion.cita.medico_id != medico.id:
        return None, None
    return sesion, medico


def _sesion_por_token(token):
    sesion = get_object_or_404(TeleconsultaSesion, token=token)
    if not sesion.token_vigente:
        raise Http404("El enlace de la teleconsulta expiró.")
    if sesion.estado in ('FINALIZADA', 'CANCELADA'):
        raise Http404("Esta teleconsulta ya finalizó.")
    return sesion


# ─────────────────────────── MÉDICO ───────────────────────────
@login_required
def abrir_sala_cita(request, cita_id):
    """Desde la agenda: crea/obtiene la sesión de una cita de teleconsulta y
    lleva al médico a su sala."""
    medico = _medico_del_usuario(request)
    if not medico:
        messages.error(request, "Solo el personal médico puede abrir la sala.")
        return redirect('home')
    cita = get_object_or_404(Cita, id=cita_id, medico=medico)
    if not cita.es_remota:
        messages.error(request, "Esta cita no es una teleconsulta.")
        return redirect('ver_agenda')
    sesion = sesion_para_cita(cita)
    return redirect('teleconsulta:sala_medico', sesion_id=sesion.id)


@login_required
def sala_medico(request, sesion_id):
    sesion, medico = _sesion_del_medico(request, sesion_id)
    if not sesion:
        messages.error(request, "No tienes acceso a esta teleconsulta.")
        return redirect('ver_agenda')

    paciente = sesion.cita.paciente
    # Panel clínico (resumen del paciente para atender sin cambiar de app)
    historias = paciente.historias.order_by('-fecha_atencion')[:3] \
        if hasattr(paciente, 'historias') else []

    enlace_paciente = request.build_absolute_uri(
        reverse('teleconsulta:entrada', args=[sesion.token]))

    EventoAuditoria.registrar(
        actor=request.user.get_username(), accion='MEDICO_ABRE_SALA',
        recurso=f'sesion:{sesion.id}', sesion=sesion, ip=get_client_ip(request))

    return render(request, 'teleconsulta/sala_medico.html', {
        'sesion': sesion, 'cita': sesion.cita, 'paciente': paciente,
        'historias': historias, 'enlace_paciente': enlace_paciente,
        'jitsi_domain': jitsi_domain(),
        'medico_nombre': request.user.get_full_name() or request.user.get_username(),
        'es_medico': bool(getattr(request.user, 'perfil_medico', None)),
    })


@login_required
def admitir(request, sesion_id):
    sesion, medico = _sesion_del_medico(request, sesion_id)
    if not sesion:
        return JsonResponse({'ok': False}, status=403)
    if request.method == 'POST':
        sesion.paciente_admitido = True
        if not sesion.inicio:
            sesion.inicio = timezone.now()
        sesion.estado = 'EN_CURSO'
        sesion.save(update_fields=['paciente_admitido', 'inicio', 'estado'])
        EventoAuditoria.registrar(
            actor=request.user.get_username(), accion='ADMITE_PACIENTE',
            recurso=f'sesion:{sesion.id}', sesion=sesion, ip=get_client_ip(request))
    return JsonResponse({'ok': True, 'estado': sesion.estado})


@login_required
def finalizar(request, sesion_id):
    sesion, medico = _sesion_del_medico(request, sesion_id)
    if not sesion:
        return redirect('ver_agenda')
    if request.method == 'POST':
        sesion.estado = 'FINALIZADA'
        sesion.fin = timezone.now()
        sesion.paciente_admitido = False
        sesion.paciente_en_espera = False
        sesion.save(update_fields=['estado', 'fin', 'paciente_admitido', 'paciente_en_espera'])
        EventoAuditoria.registrar(
            actor=request.user.get_username(), accion='FINALIZA_TELECONSULTA',
            recurso=f'sesion:{sesion.id}', sesion=sesion, ip=get_client_ip(request))
        # Al finalizar, llevar al médico a registrar la nota clínica (queda en la HC
        # única del paciente, marcada como atención remota).
        if getattr(request.user, 'perfil_medico', None):
            messages.success(
                request, "Teleconsulta finalizada. Registra la nota clínica de la atención.")
            return redirect('crear_historia', paciente_id=sesion.cita.paciente_id)
        messages.success(request, "Teleconsulta finalizada.")
    return redirect('ver_agenda')


@login_required
def derivar(request, sesion_id):
    """Escalamiento: deriva la teleconsulta a atención presencial o emergencia,
    con motivo, y cierra la sesión (seguridad clínica)."""
    sesion, medico = _sesion_del_medico(request, sesion_id)
    if not sesion:
        return redirect('ver_agenda')
    # La derivación / declaración de emergencia es un acto CLÍNICO: solo el médico.
    if not getattr(request.user, 'perfil_medico', None):
        messages.error(request, "Solo el médico puede derivar o declarar una emergencia.")
        return redirect('teleconsulta:sala_medico', sesion_id=sesion.id)
    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'PRESENCIAL')
        if tipo not in dict(TeleconsultaSesion.DERIVACION_TIPOS):
            tipo = 'PRESENCIAL'
        sesion.derivacion_tipo = tipo
        sesion.derivacion_motivo = (request.POST.get('motivo') or '').strip()[:2000]
        sesion.derivada_en = timezone.now()
        sesion.estado = 'DERIVADA'
        sesion.fin = sesion.fin or timezone.now()
        sesion.paciente_admitido = False
        sesion.paciente_en_espera = False
        sesion.save(update_fields=[
            'derivacion_tipo', 'derivacion_motivo', 'derivada_en',
            'estado', 'fin', 'paciente_admitido', 'paciente_en_espera'])
        EventoAuditoria.registrar(
            actor=request.user.get_username(), accion='DERIVA_A_' + tipo,
            recurso=f'sesion:{sesion.id}', sesion=sesion, ip=get_client_ip(request),
            motivo=sesion.derivacion_motivo,
            ubicacion=sesion.ubicacion_declarada_paciente)
        etiqueta = dict(TeleconsultaSesion.DERIVACION_TIPOS)[tipo]
        messages.warning(
            request, f"Teleconsulta derivada a: {etiqueta}. Se registró el motivo.")
    return redirect('ver_agenda')


@login_required
def estado_medico_json(request, sesion_id):
    """Polling del médico: ¿el paciente está en sala de espera?"""
    sesion, medico = _sesion_del_medico(request, sesion_id)
    if not sesion:
        return JsonResponse({'ok': False}, status=403)
    return JsonResponse({
        'ok': True, 'estado': sesion.estado,
        'paciente_en_espera': sesion.paciente_en_espera,
        'paciente_admitido': sesion.paciente_admitido,
        'consentimiento': sesion.consentimiento_aceptado,
        'ubicacion': sesion.ubicacion_declarada_paciente,
    })


# ─────────────────────────── PACIENTE (token) ───────────────────────────
def entrada(request, token):
    """Enruta al paciente según el estado de su sesión."""
    sesion = _sesion_por_token(token)
    EventoAuditoria.registrar(
        actor=f'paciente:{token[:8]}', accion='PACIENTE_ABRE_ENLACE',
        recurso=f'sesion:{sesion.id}', sesion=sesion, ip=get_client_ip(request))
    if not sesion.consentimiento_aceptado:
        return redirect('teleconsulta:consentimiento', token=token)
    if sesion.paciente_admitido:
        return redirect('teleconsulta:sala_paciente', token=token)
    return redirect('teleconsulta:precheck', token=token)


def consentimiento(request, token):
    sesion = _sesion_por_token(token)
    if sesion.consentimiento_aceptado:
        return redirect('teleconsulta:precheck', token=token)

    if request.method == 'POST':
        if request.POST.get('acepto') != 'on':
            messages.error(request, "Debes aceptar el consentimiento para continuar.")
            return redirect('teleconsulta:consentimiento', token=token)
        aceptado_por = request.POST.get('aceptado_por', 'PACIENTE')
        c = ConsentimientoTelesalud(
            sesion=sesion, paciente=sesion.cita.paciente,
            tipo='TELESALUD', version_documento=CONSENT_VERSION,
            texto_documento=CONSENT_TEXT, aceptado_por=aceptado_por,
            representante_nombre=request.POST.get('rep_nombre', '')[:150],
            representante_cedula=request.POST.get('rep_cedula', '')[:20],
            representante_parentesco=request.POST.get('rep_parentesco', '')[:50],
        )
        c.sellar(ip=get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
        sesion.estado = 'PRECHECK'
        sesion.save(update_fields=['estado'])
        EventoAuditoria.registrar(
            actor=f'paciente:{token[:8]}', accion='ACEPTA_CONSENTIMIENTO',
            recurso=f'consentimiento:{c.id}', sesion=sesion, ip=get_client_ip(request),
            version=CONSENT_VERSION, hash=c.hash_documento)
        return redirect('teleconsulta:precheck', token=token)

    return render(request, 'teleconsulta/consentimiento.html', {
        'sesion': sesion, 'token': token,
        'consent_text': CONSENT_TEXT, 'version': CONSENT_VERSION,
    })


def precheck(request, token):
    sesion = _sesion_por_token(token)
    if not sesion.consentimiento_aceptado:
        return redirect('teleconsulta:consentimiento', token=token)
    return render(request, 'teleconsulta/precheck.html', {
        'sesion': sesion, 'token': token,
    })


def listo(request, token):
    """El paciente terminó el pre-check y pasa a la sala de espera."""
    sesion = _sesion_por_token(token)
    if request.method == 'POST':
        sesion.paciente_en_espera = True
        sesion.ubicacion_declarada_paciente = (request.POST.get('ubicacion') or '')[:200]
        if sesion.estado in ('PROGRAMADA', 'CONSENTIMIENTO', 'PRECHECK'):
            sesion.estado = 'SALA_ESPERA'
        sesion.save(update_fields=['paciente_en_espera', 'ubicacion_declarada_paciente', 'estado'])
        EventoAuditoria.registrar(
            actor=f'paciente:{token[:8]}', accion='PACIENTE_EN_SALA_ESPERA',
            recurso=f'sesion:{sesion.id}', sesion=sesion, ip=get_client_ip(request),
            ubicacion=sesion.ubicacion_declarada_paciente)
    return redirect('teleconsulta:sala_espera', token=token)


def sala_espera(request, token):
    sesion = _sesion_por_token(token)
    if not sesion.consentimiento_aceptado:
        return redirect('teleconsulta:consentimiento', token=token)
    if sesion.paciente_admitido:
        return redirect('teleconsulta:sala_paciente', token=token)
    return render(request, 'teleconsulta/sala_espera.html', {
        'sesion': sesion, 'token': token,
        'medico': sesion.cita.medico,
    })


def sala_paciente(request, token):
    sesion = _sesion_por_token(token)
    if not sesion.consentimiento_aceptado:
        return redirect('teleconsulta:consentimiento', token=token)
    if not sesion.paciente_admitido:
        return redirect('teleconsulta:sala_espera', token=token)
    paciente = sesion.cita.paciente
    nombre = paciente.usuario.get_full_name() or 'Paciente'
    EventoAuditoria.registrar(
        actor=f'paciente:{token[:8]}', accion='PACIENTE_ENTRA_VIDEO',
        recurso=f'sesion:{sesion.id}', sesion=sesion, ip=get_client_ip(request))
    return render(request, 'teleconsulta/sala_paciente.html', {
        'sesion': sesion, 'token': token,
        'jitsi_domain': jitsi_domain(), 'paciente_nombre': nombre,
    })


def estado_json(request, token):
    """Polling del paciente en sala de espera."""
    sesion = get_object_or_404(TeleconsultaSesion, token=token)
    return JsonResponse({
        'estado': sesion.estado,
        'admitido': sesion.paciente_admitido,
        'finalizada': sesion.estado in ('FINALIZADA', 'CANCELADA', 'DERIVADA'),
        'derivada': sesion.estado == 'DERIVADA',
        'derivacion_tipo': sesion.derivacion_tipo,
        'derivacion_motivo': sesion.derivacion_motivo,
    })
