from datetime import date
import requests as http_requests
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from citas.models import Cita
from .forms import RegistroInicialMedicoForm, CompletarPerfilMedicoForm, SecretariaRegistroForm
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncMonth
from medico.models import Medico, Especialidad, Secretaria
from paciente.models import Paciente
from citas.views import enviar_correo_activacion
from django.contrib import messages

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail, get_connection
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import Group

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import SetPasswordForm
import ssl

from django.core.mail import send_mail
from django.http import HttpResponse
from django.contrib.auth.forms import PasswordResetForm

from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordResetConfirmView
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

@login_required
def home(request):
    # --- DICCIONARIO PARA TRADUCIR MESES ---
    MESES_ES = {
        'January': 'Ene', 'February': 'Feb', 'March': 'Mar', 'April': 'Abr',
        'May': 'May', 'June': 'Jun', 'July': 'Jul', 'August': 'Ago',
        'September': 'Sep', 'October': 'Oct', 'November': 'Nov', 'December': 'Dic'
    }

    # --- LOGICA PARA PACIENTES ---
    citas_proximas = []
    if request.user.role == 'PACIENTE':
        try:
            paciente = request.user.perfil_paciente
            citas_proximas = Cita.objects.filter(
                paciente=paciente,
                fecha__gte=date.today(),
                estado='P'
            ).order_by('fecha', 'hora')
        except:
            pass

    # --- LOGICA PARA MÉDICOS / ADMINS ---
    if request.user.role == 'MEDICO':
        try:
            medico = request.user.perfil_medico
            es_vet = medico.especialidad and 'veterin' in medico.especialidad.nombre.lower()
            from django.db.models import Q
            base_qs = Paciente.objects.filter(usuario__role='PACIENTE')
            if es_vet:
                total_pacientes = base_qs.filter(
                    Q(citas__medico=medico) | Q(mascotas__isnull=False)
                ).distinct().count()
            else:
                total_pacientes = base_qs.filter(citas__medico=medico).distinct().count()
        except AttributeError:
            total_pacientes = 0
    else:
        total_pacientes = Paciente.objects.count()
    total_medicos = Medico.objects.count()
    citas_hoy_count = 0
    grafico_meses = []
    grafico_cantidades = []

    especialidad_nombre = ""

    if request.user.role in ['ADMIN', 'MEDICO']:
        # 1. Citas de hoy (Específico por rol)
        if request.user.role == 'MEDICO':
            try:
                medico = request.user.perfil_medico
                citas_hoy_count = Cita.objects.filter(
                    medico=medico,
                    fecha=date.today(),
                    estado__in=['P', 'E']
                ).count()
                especialidad_nombre = medico.especialidad.nombre if medico.especialidad else "Médico General"
                # Datos del gráfico solo del médico logueado
                qs_grafico = Cita.objects.filter(medico=medico)
            except:
                citas_hoy_count = 0
                qs_grafico = Cita.objects.none()
                especialidad_nombre = "Personal Médico"
        else:
            # Si es ADMIN, ve todo lo de la clínica
            citas_hoy_count = Cita.objects.filter(fecha=date.today()).count()
            qs_grafico = Cita.objects.all()
        
        # 2. Datos para el Gráfico (Agrupados por mes)
        datos_grafico = qs_grafico.annotate(
            mes=TruncMonth('fecha')
        ).values('mes').annotate(
            cantidad=Count('id')
        ).order_by('mes')

        for d in datos_grafico:
            if d['mes']:
                nombre_en = d['mes'].strftime("%B")
                nombre_es = MESES_ES.get(nombre_en, nombre_en)
                grafico_meses.append(nombre_es)
                grafico_cantidades.append(d['cantidad'])

    return render(request, 'home.html', {
        'citas_proximas': citas_proximas,
        'total_pacientes': total_pacientes,
        'total_medicos': total_medicos,
        'citas_hoy': citas_hoy_count,
        'grafico_meses': grafico_meses, 
        'grafico_cantidades': grafico_cantidades,
        'especialidad': especialidad_nombre,
    })

User = get_user_model() # 👈 Esto detecta automáticamente que es 'users.User'

def registro_medico(request):
    if request.method == 'POST':
        form = RegistroInicialMedicoForm(request.POST)
        if form.is_valid():
            # Extraemos los datos limpios (copia profunda para evitar problemas de referencia)
            datos = form.cleaned_data.copy()
            
            # Convertir objetos modelo a valores serializables para la sesión
            if datos.get('especialidad'):
                try:
                    datos['especialidad'] = datos['especialidad'].id
                except AttributeError:
                    pass
            if datos.get('pais'):
                try:
                    datos['pais'] = datos['pais'].nombre
                except AttributeError:
                    pass
            if datos.get('ciudad'):
                try:
                    datos['ciudad'] = datos['ciudad'].nombre
                except AttributeError:
                    pass

            import uuid, json
            from users.models import RegistroPendiente
            client_tx_id = str(uuid.uuid4())
            reg = RegistroPendiente(client_transaction_id=client_tx_id)
            reg.set_datos(datos)
            reg.save()
            request.session['payphone_client_tx'] = client_tx_id
            request.session.modified = True

            return redirect('pasarela_pago')
        else:
            # Si el formulario no es válido, imprimimos los errores en la terminal
            print("ERRORES DEL FORMULARIO:", form.errors)
    else:
        form = RegistroInicialMedicoForm()
    
    return render(request, 'registro_medico.html', {'form': form})
from django.urls import reverse

def pasarela_pago(request):
    from users.models import RegistroPendiente
    client_transaction_id = request.session.get('payphone_client_tx')
    if not client_transaction_id:
        return redirect('registro_medico')
    try:
        reg = RegistroPendiente.objects.get(client_transaction_id=client_transaction_id)
        datos = reg.get_datos()
    except RegistroPendiente.DoesNotExist:
        return redirect('registro_medico')

    base_url = f"{request.scheme}://{request.get_host()}"

    payload = {
        "amount": 5000,               # centavos: $50.00
        "amountWithTax": 0,
        "amountWithoutTax": 5000,
        "tax": 0,
        "currency": "USD",
        "storeId": settings.PAYPHONE_STORE_ID,
        "reference": f"Suscripcion-{datos.get('username', 'medico')}",
        "clientTransactionId": client_transaction_id,
        "responseUrl": f"{base_url}/confirmar-pago/",
        "cancellationUrl": f"{base_url}/registro-medico/",
    }

    try:
        resp = http_requests.post(
            "https://pay.payphonetodoesposible.com/api/button/Prepare",
            json=payload,
            headers={"Authorization": f"Bearer {settings.PAYPHONE_TOKEN}"},
            timeout=15,
        )
        print(f"DEBUG PAYPHONE status: {resp.status_code}")
        print(f"DEBUG PAYPHONE response: {resp.text}")
        resp.raise_for_status()
        data = resp.json()
        payment_url = data.get("payWithCard") or data.get("payWithPayPhone")
        if not payment_url:
            raise ValueError(f"No se recibió URL de pago: {data}")
        print(f"DEBUG PAYPHONE url: {payment_url}")
        return redirect(payment_url)
    except Exception as e:
        messages.error(request, f"Error al iniciar el pago: {e}")
        return redirect('registro_medico')

# --- VISTA 1: CREA EL USUARIO Y SALTA A LA CONTRASEÑA ---
@login_required
def crear_secretaria(request):
    role = getattr(request.user, 'role', '')

    if role == 'ADMIN':
        medico_id = request.GET.get('medico_id') or request.POST.get('medico_id')
        medico_actual = Medico.objects.filter(id=medico_id).first() if medico_id else None
        secretarias_actuales = Secretaria.objects.select_related('usuario', 'medico__usuario').filter(usuario__is_active=True)
        medicos_disponibles = Medico.objects.select_related('usuario').all()
    elif hasattr(request.user, 'perfil_medico'):
        medico_actual = request.user.perfil_medico
        secretarias_actuales = Secretaria.objects.filter(medico=medico_actual, usuario__is_active=True)
        medicos_disponibles = None
    else:
        messages.error(request, "Acceso denegado.")
        return redirect('home')
    
    # Detectamos si el usuario envió un ID oculto para editar
    secretaria_id = request.POST.get('secretaria_id_hidden')
    
    if request.method == 'POST':
        if secretaria_id:
            # --- LÓGICA DE EDICIÓN (SOLO EMAIL Y CELULAR) ---
            try:
                sec_instancia = get_object_or_404(Secretaria, id=secretaria_id, medico=medico_actual)
                user_sec = sec_instancia.usuario
                
                # Actualizamos solo los campos permitidos
                user_sec.email = request.POST.get('email')
                user_sec.save()
                
                # Suponiendo que tienes el campo 'telefono' en tu modelo Secretaria
                sec_instancia.telefono = request.POST.get('telefono')
                sec_instancia.save()
                
                messages.success(request, f"Datos de {user_sec.first_name} actualizados correctamente.")
                return redirect('crear_secretaria')
            except Exception as e:
                messages.error(request, f"Error al actualizar: {e}")
        else:
            # --- TU LÓGICA ORIGINAL DE REGISTRO (SIN CAMBIOS) ---
            form = SecretariaRegistroForm(request.POST)
            if form.is_valid():
                user = None 
                try:
                    with transaction.atomic():
                        cd = form.cleaned_data
                        user = User.objects.create_user(
                            username=cd['username'],
                            email=cd['email'],
                            first_name=cd['first_name'],
                            last_name=cd['last_name'],
                            cedula=cd.get('cedula'),
                            role='SECRETARIA',
                            is_active=False,
                        )
                        user.set_unusable_password()
                        user.save()

                        medico_para_crear = medico_actual
                        if role == 'ADMIN':
                            medico_id_post = request.POST.get('medico_id')
                            medico_para_crear = Medico.objects.filter(id=medico_id_post).first()
                            if not medico_para_crear:
                                raise ValueError("Debe seleccionar un médico.")

                        Secretaria.objects.create(
                            usuario=user,
                            medico=medico_para_crear,
                            telefono=request.POST.get('telefono'),
                        )
                        
                        from django.contrib.auth.models import Group
                        grupo, _ = Group.objects.get_or_create(name='Secretarias')
                        user.groups.add(grupo)

                    try:
                        enviar_correo_activacion(request, user)
                        messages.success(
                            request,
                            f"✔ Secretaria {user.get_full_name()} registrada correctamente. "
                            f"Se envió un correo a {user.email} para que cree su contraseña y pueda ingresar al sistema."
                        )
                    except Exception as mail_error:
                        messages.warning(
                            request,
                            f"Secretaria {user.get_full_name()} creada, pero el correo no se pudo enviar ({mail_error}). "
                            f"Usa 'Asignar Contraseña' para darle acceso manualmente."
                        )
                    
                    return redirect('crear_secretaria') 

                except Exception as e:
                    messages.error(request, f"Error en la base de datos: {e}")
    else:
        form = SecretariaRegistroForm()

    return render(request, 'crear_secretaria.html', {
        'form': form,
        'secretarias': secretarias_actuales,
        'medicos_disponibles': medicos_disponibles,
        'es_admin': role == 'ADMIN',
    })

# 3. Nueva función para eliminar
@login_required
def eliminar_secretaria(request, secretaria_id):
    # Solo puede eliminarla el médico al que pertenece
    secretaria = get_object_or_404(Secretaria, id=secretaria_id, medico=request.user.perfil_medico)
    user_asociado = secretaria.usuario
    
    nombre = user_asociado.get_full_name()
    user_asociado.delete() # Esto borra el User y la Secretaria por el CASCADE
    
    messages.success(request, f"Acceso de {nombre} eliminado correctamente.")
    return redirect('crear_secretaria')

@login_required
def asignar_password(request, user_id):
    # Solo ADMIN o el médico que creó al usuario puede asignar contraseñas
    role = getattr(request.user, 'role', '')
    if role not in ('ADMIN', 'MEDICO'):
        messages.error(request, "No tiene permisos para realizar esta acción.")
        return redirect('home')

    user = get_object_or_404(User, id=user_id)

    # Si es médico, solo puede asignar contraseña a sus propias secretarias
    if role == 'MEDICO' and user.role == 'SECRETARIA':
        if not Secretaria.objects.filter(usuario=user, medico__usuario=request.user).exists():
            messages.error(request, "No tiene permisos sobre este usuario.")
            return redirect('home')
    elif role == 'MEDICO' and user.role != 'SECRETARIA':
        messages.error(request, "No tiene permisos sobre este usuario.")
        return redirect('home')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            user = form.save()

            # Protección: solo asigna MEDICO si el usuario es nuevo o PACIENTE
            if user.role in [None, 'PACIENTE', '']:
                 user.role = 'MEDICO'

            # Activar cuenta al establecer la contraseña
            user.is_active = True
            user.save()

            messages.success(request, "Contraseña establecida correctamente. Ya puede iniciar sesión.")
            return redirect('login')
    else:
        form = SetPasswordForm(user)
    
    return render(request, 'asignar_password.html', {'form': form, 'user_obj': user})

class ActivarCuentaConfirmView(PasswordResetConfirmView):
    """
    Igual que PasswordResetConfirmView pero activa la cuenta al guardar la contraseña.
    Usado cuando una secretaria o médico nuevo establece su contraseña por primera vez.
    """
    template_name = 'registration/password_reset_confirm.html'
    success_url = '/login/'

    def form_valid(self, form):
        user = form.save()
        user.is_active = True
        user.save(update_fields=['is_active'])
        messages.success(
            self.request,
            f"Contraseña creada correctamente. Ya puedes iniciar sesión, {user.first_name}."
        )
        return redirect('login')


@login_required
def redirect_by_role(request):
    # Obtenemos el rol del usuario que acaba de loguearse
    #user_role = getattr(request.user, 'role', None)
    request.user.refresh_from_db()

    if request.user.role == 'SECRETARIA':
        return redirect('dashboard_secretaria')
    elif request.user.role == 'MEDICO':
        return redirect('home')  # O el dashboard del médico
    elif request.user.role == 'ADMIN':
        return redirect('home')
    else:
        return redirect('home')
    
@login_required
def probar_email(request):
    if getattr(request.user, 'role', '') != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('home')
    try:
        asunto = 'Prueba de Conexión VertexSalud'
        mensaje = 'Si recibes esto, la configuración de Gmail en VertexSalud es correcta.'
        email_remitente = settings.EMAIL_HOST_USER
        # Pon tu correo personal aquí para la prueba
        email_destino = ['tu-correo-personal@gmail.com'] 

        send_mail(asunto, mensaje, email_remitente, email_destino)
        
        return HttpResponse("<h1>✅ ¡Éxito!</h1><p>El correo de prueba ha sido enviado. Revisa tu bandeja de entrada (y la carpeta de Spam).</p>")
    except Exception as e:
        return HttpResponse(f"<h1>❌ Error de Configuración</h1><p>Detalles: {str(e)}</p>")
    
def pago_exitoso(request):
    return render(request, 'pago_exitoso.html')

def registro_exitoso(request):
    email = request.session.pop('registro_email', None)
    return render(request, 'registro_exitoso.html', {'email': email or 'tu correo registrado'})

def proceso_pago_medico(request):
    context = {
        'paypal_client_id': 'TU_CLIENT_ID_DE_SANDBOX',
        'monto': '50.00'
    }
    return render(request, 'pago_registro_medico.html', context)

@transaction.atomic
def confirmar_pago(request):
    """
    PayPhone redirige aquí con ?transactionId=...&clientTransactionId=...
    Verificamos el pago contra la API de PayPhone y, si es exitoso, creamos el médico.
    """
    from medico.models import Medico, Especialidad

    print(f"DEBUG CONFIRMAR GET params: {dict(request.GET)}")
    print(f"DEBUG CONFIRMAR POST params: {dict(request.POST)}")

    transaction_id        = request.GET.get('id') or request.GET.get('transactionId') or request.POST.get('transactionId')
    client_transaction_id = request.GET.get('clientTransactionId') or request.POST.get('clientTransactionId')

    print(f"DEBUG transactionId={transaction_id} clientTransactionId={client_transaction_id}")

    if not transaction_id or not client_transaction_id:
        messages.error(request, "No se recibieron los datos de confirmación del pago.")
        return redirect('registro_medico')

    # 1. Verificar el pago con PayPhone
    try:
        resp = http_requests.post(
            "https://pay.payphonetodoesposible.com/api/button/V2/Confirm",
            json={"id": int(transaction_id), "clientTxId": client_transaction_id},
            headers={"Authorization": f"Bearer {settings.PAYPHONE_TOKEN}"},
            timeout=20,
        )
        print(f"DEBUG CONFIRM status: {resp.status_code} body: {resp.text}")
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        messages.error(request, f"No se pudo verificar el pago: {e}")
        return redirect('registro_medico')

    status_code = data.get("transactionStatus") or data.get("statusCode") or ""
    if str(status_code) not in ("3", "approved", "Approved"):
        messages.error(request, f"El pago no fue aprobado (estado: {status_code}). Intente nuevamente.")
        return redirect('registro_medico')

    # 2. Recuperar datos desde BD
    from users.models import RegistroPendiente
    try:
        reg = RegistroPendiente.objects.get(client_transaction_id=client_transaction_id)
        datos = reg.get_datos()
    except RegistroPendiente.DoesNotExist:
        messages.error(request, "Registro no encontrado. Por favor regístrese nuevamente.")
        return redirect('registro_medico')

    # 3. Crear usuario y médico
    try:
        User = get_user_model()
        user = User.objects.create_user(
            username=datos.get('username'),
            email=datos.get('email'),
            password=None,
            first_name=datos.get('first_name'),
            last_name=datos.get('last_name'),
            cedula=datos.get('cedula'),
            role='MEDICO',
            is_active=True,
            pago_realizado=True,
        )
        user.set_unusable_password()
        user.save()

        especialidad_id = datos.get('especialidad')
        especialidad_obj = Especialidad.objects.filter(id=especialidad_id).first() if especialidad_id else None

        medico_obj = Medico.objects.create(
            usuario=user,
            especialidad=especialidad_obj,
            pais=datos.get('pais', ''),
            ciudad=datos.get('ciudad', ''),
            sector=datos.get('sector', ''),
        )

        import threading
        host = request.get_host()
        scheme = request.scheme

        def tareas_segundo_plano(u, m, host, scheme):
            try:
                print(f"[EMAIL] Enviando correo de activación a {u.email}...")
                from django.contrib.auth.tokens import default_token_generator
                from django.utils.http import urlsafe_base64_encode
                from django.utils.encoding import force_bytes

                token = default_token_generator.make_token(u)
                uid   = urlsafe_base64_encode(force_bytes(u.pk))
                link  = f"{scheme}://{host}/reset/{uid}/{token}/"
                asunto = "Bienvenida a VertexSalud - Activa tu cuenta de Médico"
                html_body = (
                    f"<p>Hola <b>{u.first_name}</b>,</p>"
                    f"<p>Se ha creado tu perfil de médico en el sistema.</p>"
                    f"<p>Para activar tu cuenta y configurar tu contraseña, haz clic en el siguiente enlace:</p>"
                    f'<p><a href="{link}">{link}</a></p>'
                    f"<p>Si no solicitaste esta cuenta, por favor ignora este mensaje.</p>"
                )

                if not settings.RESEND_API_KEY:
                    raise RuntimeError("RESEND_API_KEY no configurado")

                resp = http_requests.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": settings.RESEND_FROM,
                        "to": [u.email],
                        "subject": asunto,
                        "html": html_body,
                    },
                    timeout=15,
                )
                print(f"[EMAIL] Resend status={resp.status_code} body={resp.text[:200]}")
                resp.raise_for_status()
                print(f"[EMAIL] Correo enviado exitosamente a {u.email}")
            except Exception as e:
                import traceback
                print(f"[EMAIL ERROR] {e}")
                print(traceback.format_exc())

            try:
                from facturacion.services.sri import SriService
                from decimal import Decimal
                SriService().crear_factura_pago(m, Decimal('50.00'))
            except Exception as e:
                print(f"[FACTURACIÓN] {e}")

        threading.Thread(target=tareas_segundo_plano, args=(user, medico_obj, host, scheme), daemon=True).start()

        email_registrado = datos.get('email', '')
        reg.delete()
        request.session.pop('payphone_client_tx', None)
        request.session['registro_email'] = email_registrado

        return redirect('registro_exitoso')

    except Exception as e:
        messages.error(request, f"Pago recibido pero error al crear la cuenta: {e}")
        return redirect('registro_medico')


@login_required
def panel_admin(request):
    if getattr(request.user, 'role', '') != 'ADMIN':
        messages.error(request, 'Acceso denegado.')
        return redirect('home')

    from django.utils import timezone
    from django.db.models import Sum, Count
    from facturacion.models import FacturaElectronica

    hoy = timezone.now().date()
    mes_actual = hoy.replace(day=1)

    User = get_user_model()

    # ── Estadísticas generales ──────────────────────────────────────────────
    total_medicos     = Medico.objects.count()
    total_pacientes   = Paciente.objects.count()
    total_secretarias = Secretaria.objects.count()
    citas_hoy         = Cita.objects.filter(fecha=hoy).count()
    citas_pendientes  = Cita.objects.filter(fecha=hoy, estado='P').count()

    # ── Facturación del mes ─────────────────────────────────────────────────
    facturas_mes = FacturaElectronica.objects.filter(fecha_emision__date__gte=mes_actual)
    ingresos_mes = facturas_mes.filter(estado='AUTORIZADA').aggregate(t=Sum('total'))['t'] or 0
    facturas_autorizadas = facturas_mes.filter(estado='AUTORIZADA').count()
    facturas_error       = facturas_mes.filter(estado__in=['RECHAZADA', 'ERROR']).count()

    # ── Lista médicos ───────────────────────────────────────────────────────
    medicos = Medico.objects.select_related('usuario', 'especialidad').order_by('usuario__last_name')

    # ── Lista secretarias ───────────────────────────────────────────────────
    secretarias = Secretaria.objects.select_related('usuario', 'medico__usuario').order_by('usuario__last_name')

    # ── Últimas facturas ────────────────────────────────────────────────────
    ultimas_facturas = FacturaElectronica.objects.order_by('-fecha_emision')[:10]

    return render(request, 'panel_admin.html', {
        'total_medicos':      total_medicos,
        'total_pacientes':    total_pacientes,
        'total_secretarias':  total_secretarias,
        'citas_hoy':          citas_hoy,
        'citas_pendientes':   citas_pendientes,
        'ingresos_mes':       ingresos_mes,
        'facturas_autorizadas': facturas_autorizadas,
        'facturas_error':     facturas_error,
        'medicos':            medicos,
        'secretarias':        secretarias,
        'ultimas_facturas':   ultimas_facturas,
        'hoy':                hoy,
    })


def contacto(request):
    """Formulario de contacto / sugerencias. Envía a contacto@vertexjd.com vía Resend."""
    if request.method == 'POST':
        nombre  = request.POST.get('nombre', '').strip()
        email   = request.POST.get('email', '').strip()
        asunto  = request.POST.get('asunto', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        tipo    = request.POST.get('tipo', 'CONTACTO')

        if not (nombre and email and mensaje):
            messages.error(request, "Por favor completa todos los campos requeridos.")
            return render(request, 'contacto.html', {
                'datos': {'nombre': nombre, 'email': email, 'asunto': asunto, 'mensaje': mensaje, 'tipo': tipo}
            })

        try:
            etiqueta = "SUGERENCIA" if tipo == 'SUGERENCIA' else "CONTACTO"
            asunto_email = f"[{etiqueta}] {asunto or 'Mensaje desde VertexSalud'}"
            html = (
                f"<p><strong>Tipo:</strong> {etiqueta}</p>"
                f"<p><strong>Nombre:</strong> {nombre}</p>"
                f"<p><strong>Correo:</strong> {email}</p>"
                f"<p><strong>Asunto:</strong> {asunto or '(sin asunto)'}</p>"
                f"<hr><p><strong>Mensaje:</strong></p>"
                f"<p>{mensaje.replace(chr(10), '<br>')}</p>"
            )

            resp = http_requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.RESEND_FROM,
                    "to": ["contacto@vertexjd.com"],
                    "reply_to": email,
                    "subject": asunto_email,
                    "html": html,
                },
                timeout=15,
            )
            print(f"[CONTACTO] Resend status={resp.status_code} body={resp.text[:200]}")
            resp.raise_for_status()
            messages.success(request, "¡Mensaje enviado! Te responderemos pronto a tu correo.")
            return redirect('contacto')
        except Exception as e:
            print(f"[CONTACTO ERROR] {e}")
            messages.error(request, "No se pudo enviar el mensaje. Intenta nuevamente.")

    return render(request, 'contacto.html', {})
