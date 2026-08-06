"""Ficha pública del médico: página SEO sin login + solicitudes de cita.

- ficha_publica: página pública en /p/<slug>/ (schema.org Physician). Recibe
  solicitudes de cita (crea SolicitudCita "pendiente" y notifica al médico).
- FichaEditView: el médico logueado edita su ficha (mapa CARTO + Photon).
- ficha_qr: PNG del QR de la URL pública.
- solicitudes_cita / cambiar_estado_solicitud: bandeja de solicitudes del médico.
"""
import io

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from medico.models import Especialidad, FichaPublica, Medico
from citas.models import SolicitudCita


# ── Helpers ────────────────────────────────────────────────────────────────
def _telefono_a_whatsapp(numero):
    """Normaliza a formato wa.me para Ecuador (09XXXXXXXX -> 5939XXXXXXXX)."""
    d = "".join(c for c in (numero or "") if c.isdigit())
    if not d:
        return ""
    if d.startswith("0"):
        d = "593" + d[1:]
    elif not d.startswith("593"):
        d = "593" + d
    return d


def _medico_del_usuario(request):
    """Devuelve el Medico del usuario (médico dueño o su secretaria)."""
    medico = getattr(request.user, "perfil_medico", None)
    if medico:
        return medico
    perfil_sec = getattr(request.user, "perfil_secretaria", None)
    return perfil_sec.medico if perfil_sec else None


def _notificar_medico(request, medico, solicitud):
    """Avisa al médico por Resend HTTP API (el SMTP está bloqueado en el hosting)."""
    email = getattr(medico.usuario, "email", "")
    if not email or not getattr(settings, "RESEND_API_KEY", ""):
        return
    try:
        import requests as http
        panel = request.build_absolute_uri(reverse("solicitudes_cita"))
        html = (
            f"<p>Estimado/a {medico.usuario.get_full_name() or 'doctor/a'},</p>"
            f"<p>Recibió una <b>nueva solicitud de cita</b> desde su ficha pública:</p>"
            f"<ul>"
            f"<li><b>Paciente:</b> {solicitud.nombre}</li>"
            f"<li><b>Teléfono:</b> {solicitud.telefono}</li>"
            f"<li><b>Motivo:</b> {solicitud.motivo or '(no indicado)'}</li>"
            f"</ul>"
            f'<p><a href="{panel}" style="background:#0d6efd;color:#fff;padding:10px 18px;'
            f'text-decoration:none;border-radius:6px;">Ver mis solicitudes de cita</a></p>'
            f"<p style='color:#888;font-size:12px'>VertexSalud</p>"
        )
        http.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.RESEND_FROM,
                "to": [email],
                "subject": "Nueva solicitud de cita — VertexSalud",
                "html": html,
            },
            timeout=15,
        )
    except Exception as e:  # nunca romper el flujo público por el correo
        print(f"[FICHA notificar_medico] {e}")


# ── Página pública (sin login) ───────────────────────────────────────────────
def ficha_publica(request, slug):
    """Ficha pública del médico (SEO). Capta pacientes que solicitan cita."""
    ficha = get_object_or_404(FichaPublica, slug=slug)
    medico = ficha.medico
    if not ficha.publicada:
        raise Http404("Ficha no disponible.")

    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        tel = (request.POST.get("telefono") or "").strip()
        motivo = (request.POST.get("motivo") or "").strip()
        tel_digits = "".join(c for c in tel if c.isdigit())
        if not nombre or len(tel_digits) < 7:
            messages.error(request, "Escribe tu nombre y un teléfono válido.")
            return redirect("ficha_publica", slug=slug)

        solicitud = SolicitudCita.objects.create(
            medico=medico,
            nombre=nombre[:150],
            telefono=tel[:30],
            motivo=motivo[:1000],
            estado="pendiente",
            origen="ficha_publica",
        )
        _notificar_medico(request, medico, solicitud)
        messages.success(
            request, "¡Gracias! El médico te contactará para coordinar tu cita.")
        return redirect("ficha_publica", slug=slug)

    numero_wa = ficha.whatsapp or ficha.telefono
    wa = _telefono_a_whatsapp(numero_wa) if numero_wa else ""
    nombre_medico = (medico.usuario.get_full_name() or "").strip() or medico.usuario.username
    return render(request, "public/ficha.html", {
        "medico": medico,
        "ficha": ficha,
        "nombre_medico": nombre_medico,
        "wa_link": f"https://wa.me/{wa}" if wa else "",
    })


# ── Edición de la ficha (con login) ──────────────────────────────────────────
@method_decorator(login_required, name="dispatch")
class FichaEditView(View):
    template_name = "medico/ficha_form.html"

    def get(self, request):
        medico = getattr(request.user, "perfil_medico", None)
        if not medico:
            messages.error(request, "Solo los médicos tienen ficha pública.")
            return redirect("home")
        ficha, _ = FichaPublica.objects.get_or_create(medico=medico)
        especialidades = list(
            Especialidad.objects.order_by("nombre").values_list("nombre", flat=True))
        return render(request, self.template_name, {
            "ficha": ficha,
            "especialidades": especialidades,
            "esp_es_otra": bool(ficha.titulo_profesional) and ficha.titulo_profesional not in especialidades,
            "url_publica": request.build_absolute_uri(
                reverse("ficha_publica", args=[ficha.slug])),
        })

    def post(self, request):
        medico = getattr(request.user, "perfil_medico", None)
        if not medico:
            return redirect("home")
        ficha, _ = FichaPublica.objects.get_or_create(medico=medico)
        g = request.POST.get
        ficha.titulo_profesional = (g("titulo_profesional") or "").strip()[:120]
        ficha.descripcion = (g("descripcion") or "").strip()
        ficha.servicios = (g("servicios") or "").strip()
        ficha.ciudad = (g("ciudad") or "").strip()[:100]
        ficha.direccion = (g("direccion") or "").strip()[:255]
        try:
            ficha.lat = float(g("lat")) if (g("lat") or "").strip() else None
            ficha.lng = float(g("lng")) if (g("lng") or "").strip() else None
        except (ValueError, TypeError):
            ficha.lat = ficha.lng = None
        ficha.mapa_url = (
            f"https://www.google.com/maps?q={ficha.lat},{ficha.lng}"
            if ficha.lat is not None and ficha.lng is not None else "")
        ficha.telefono = (g("telefono") or "").strip()[:30]
        ficha.whatsapp = (g("whatsapp") or "").strip()[:30]
        ficha.horarios = (g("horarios") or "").strip()
        precio_raw = (g("precio_consulta") or "").strip().replace(",", ".")
        try:
            ficha.precio_consulta = float(precio_raw) if precio_raw else None
        except (ValueError, TypeError):
            ficha.precio_consulta = None
        ficha.publicada = g("publicada") == "on"
        ficha.save()
        messages.success(request, "¡Ficha guardada!")
        return redirect("ficha_editar")


@login_required
def ficha_qr(request):
    """PNG del QR de la ficha pública (para imprimir)."""
    medico = getattr(request.user, "perfil_medico", None)
    if not medico:
        raise Http404()
    ficha, _ = FichaPublica.objects.get_or_create(medico=medico)
    url = request.build_absolute_uri(reverse("ficha_publica", args=[ficha.slug]))
    import qrcode
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


# ── Bandeja de solicitudes (con login) ───────────────────────────────────────
@login_required
def solicitudes_cita(request):
    medico = _medico_del_usuario(request)
    if not medico:
        messages.error(request, "Solo médicos o secretarias ven solicitudes de cita.")
        return redirect("home")
    ver = request.GET.get("ver", "activas")
    qs = SolicitudCita.objects.filter(medico=medico)
    if ver != "todas":
        # Bandeja activa: siguen requiriendo acción (aún no se agendaron ni descartaron)
        qs = qs.filter(estado__in=["pendiente", "contactada"])
    return render(request, "medico/solicitudes_cita.html", {
        "solicitudes": qs,
        "ver": ver,
        "total_activas": SolicitudCita.objects.filter(
            medico=medico, estado__in=["pendiente", "contactada"]).count(),
    })


@login_required
def cambiar_estado_solicitud(request, sol_id, accion):
    if request.method != "POST":
        return redirect("solicitudes_cita")
    medico = _medico_del_usuario(request)
    if not medico:
        return redirect("home")
    sol = get_object_or_404(SolicitudCita, id=sol_id, medico=medico)
    if accion in {"contactada", "agendada", "descartada", "pendiente"}:
        sol.estado = accion
        sol.save(update_fields=["estado"])
        messages.success(request, f"Solicitud de {sol.nombre}: {sol.get_estado_display()}.")
    return redirect("solicitudes_cita")
