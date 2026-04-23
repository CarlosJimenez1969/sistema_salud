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

    # 1. LÓGICA DE RESCATE (Igual que en la vista de impresión)
    texto_seguridad = "Fiebre persistente, dificultad para respirar, dolor abdominal intenso o pérdida del conocimiento."
    # Usamos strip() para limpiar espacios en blanco accidentales
    signos_alarma = historia.signos_alarma.strip() if historia.signos_alarma else texto_seguridad

    # 2. Generar el contenido HTML para el PDF
    template_path = 'historia/receta_pdf.html' 
    context = {
        'h': historia,
        'signos_alarma_print': signos_alarma  # <-- IMPORTANTE: Pasamos la variable corregida
    }
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
    
    email = EmailMessage(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [paciente_user.email],
    )
    
    # 5. Adjuntar el PDF generado
    pdf_value = pdf_result.getvalue()
    # Limpiamos el nombre del archivo de espacios
    filename = f"Receta_{paciente_user.last_name}_{historia.id}.pdf".replace(" ", "_")
    email.attach(filename, pdf_value, 'application/pdf')

    # 6. Enviar
    try:
        email.send()
        return True, "Correo enviado con éxito."
    except Exception as e:
        return False, f"Error al enviar el correo: {str(e)}"