from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template, render_to_string
from xhtml2pdf import pisa
from django.core.mail import EmailMessage
from django.conf import settings

def render_to_pdf(template_src, context_dict={}):
    """Convierte un HTML en un objeto HttpResponse tipo PDF"""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def enviar_receta_email(historia):
    """Genera el PDF en memoria y lo envía al correo del paciente"""
    paciente_user = historia.paciente.usuario
    print(f"[RECETA EMAIL] Iniciando envío. paciente_id={historia.paciente.id} email='{paciente_user.email}' historia_id={historia.id}")
    if not paciente_user.email:
        print("[RECETA EMAIL] Paciente sin correo registrado. Abortando.")
        return False, "El paciente no tiene un correo electrónico registrado."

    # Si ya hay un PDF guardado, lo reutilizamos; sino lo generamos y guardamos
    pdf_result = BytesIO()
    if historia.receta_pdf:
        try:
            historia.receta_pdf.open('rb')
            pdf_result.write(historia.receta_pdf.read())
            historia.receta_pdf.close()
        except Exception:
            pdf_result = BytesIO()

    if pdf_result.getbuffer().nbytes == 0:
        from django.core.files.base import ContentFile
        html = render_to_string('historia/receta_pdf.html', {'h': historia})
        pisa.pisaDocument(BytesIO(html.encode("UTF-8")), pdf_result)
        # Guardar en Cloudinary para reuso futuro
        historia.receta_pdf.save(
            f"receta_{historia.id}.pdf",
            ContentFile(pdf_result.getvalue()),
            save=True,
        )
    
    # 4. Configurar el correo
    subject = f"Receta Médica - SaludDigital - {historia.fecha_atencion.strftime('%d/%m/%Y')}"
    message = (
        f"Estimado(a) {paciente_user.first_name} {paciente_user.last_name},\n\n"
        f"Adjunto encontrará su receta médica e indicaciones generadas en su consulta de hoy.\n\n"
        f"Atentamente,\n"
        f"Dr. {historia.medico.usuario.last_name}\n"
        f"Sistema SaludDigital"
    )
    
    pdf_value = pdf_result.getvalue()
    filename = f"Receta_{paciente_user.last_name}_{historia.id}.pdf".replace(" ", "_")

    # Enviar vía Resend HTTP API (Render bloquea SMTP)
    if getattr(settings, 'RESEND_API_KEY', ''):
        import requests as http_requests
        import base64
        try:
            html_body = message.replace('\n', '<br>')
            print(f"[RECETA EMAIL] Enviando a {paciente_user.email} desde {settings.RESEND_FROM}, pdf_size={len(pdf_value)} bytes")
            resp = http_requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.RESEND_FROM,
                    "to": [paciente_user.email],
                    "subject": subject,
                    "html": html_body,
                    "attachments": [{
                        "filename": filename,
                        "content": base64.b64encode(pdf_value).decode('ascii'),
                    }],
                },
                timeout=20,
            )
            print(f"[RECETA EMAIL] Resend status={resp.status_code} body={resp.text[:300]}")
            resp.raise_for_status()
            return True, "Correo enviado con éxito."
        except Exception as e:
            import traceback
            print(f"[RECETA EMAIL ERROR] {e}")
            print(traceback.format_exc())
            return False, f"Error al enviar el correo: {str(e)}"
    else:
        print("[RECETA EMAIL] RESEND_API_KEY no configurada, intentando SMTP (fallará en Render)")

    # Fallback SMTP
    email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [paciente_user.email])
    email.attach(filename, pdf_value, 'application/pdf')
    try:
        email.send()
        return True, "Correo enviado con éxito."
    except Exception as e:
        return False, f"Error al enviar el correo: {str(e)}"