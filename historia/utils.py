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
    if not paciente_user.email:
        return False, "El paciente no tiene un correo electrónico registrado."

    template_path = 'historia/receta_pdf.html'
    context = {'h': historia}
    html = render_to_string(template_path, context)
    
    # 3. Crear el PDF en memoria (BytesIO)
    pdf_result = BytesIO()
    pisa.pisaDocument(BytesIO(html.encode("UTF-8")), pdf_result)
    
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
            print(f"[RECETA EMAIL] Resend status={resp.status_code} body={resp.text[:200]}")
            resp.raise_for_status()
            return True, "Correo enviado con éxito."
        except Exception as e:
            return False, f"Error al enviar el correo: {str(e)}"

    # Fallback SMTP
    email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [paciente_user.email])
    email.attach(filename, pdf_value, 'application/pdf')
    try:
        email.send()
        return True, "Correo enviado con éxito."
    except Exception as e:
        return False, f"Error al enviar el correo: {str(e)}"