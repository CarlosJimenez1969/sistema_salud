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

from django.contrib.auth import get_user_model # 👈 IMPORTANTE: Esto busca tu modelo real

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
            
            # Convertimos el objeto Especialidad a su ID
            if datos.get('especialidad'):
                # Si es un objeto de modelo, extraemos el ID
                try:
                    datos['especialidad'] = datos['especialidad'].id 
                except AttributeError:
                    # Si ya es un ID (porque falló antes), lo dejamos así
                    pass
            
            # Guardamos en la sesión
            request.session['datos_registro_pendiente'] = datos
            # IMPORTANTE: Forzamos el guardado de la sesión
            request.session.modified = True
            
            print("DEBUG: Datos guardados en sesión, redirigiendo a pasarela...")
            return redirect('pasarela_pago')
        else:
            # Si el formulario no es válido, imprimimos los errores en la terminal
            print("ERRORES DEL FORMULARIO:", form.errors)
    else:
        form = RegistroInicialMedicoForm()
    
    return render(request, 'registro_medico.html', {'form': form})
from django.urls import reverse

def pasarela_pago(request):
    datos = request.session.get('datos_registro_pendiente')
    if not datos:
        return redirect('registro_medico')

    context = {
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        'paypal_mode': settings.PAYPAL_MODE,
        'monto': '50.00',
        'nombre_medico': datos.get('first_name'),
    }
    return render(request, 'pasarela_pago.html', context)


# ─── Helpers PayPal ────────────────────────────────────────────────────────────

def _paypal_base_url():
    if settings.PAYPAL_MODE == 'live':
        return 'https://api-m.paypal.com'
    return 'https://api-m.sandbox.paypal.com'

def _paypal_access_token():
    """Obtiene un Bearer token usando las credenciales del servidor."""
    url = f'{_paypal_base_url()}/v1/oauth2/token'
    resp = http_requests.post(
        url,
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={'grant_type': 'client_credentials'},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()['access_token']


# ─── Vista AJAX: el servidor crea la orden en PayPal ──────────────────────────

@require_POST
def crear_orden_paypal(request):
    """
    El frontend llama a esta vista para que el SERVIDOR cree la orden en PayPal.
    Devuelve el orderID generado por PayPal.
    Sin sesión válida no se crea nada.
    """
    from django.http import JsonResponse

    if not request.session.get('datos_registro_pendiente'):
        return JsonResponse({'error': 'Sesión de registro no encontrada.'}, status=400)

    try:
        token = _paypal_access_token()
        url = f'{_paypal_base_url()}/v2/checkout/orders'
        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {'currency_code': 'USD', 'value': '50.00'},
                'description': 'Registro de suscripción - Sistema Salud',
            }],
        }
        resp = http_requests.post(
            url,
            json=payload,
            headers={'Authorization': f'Bearer {token}'},
            timeout=15,
        )
        resp.raise_for_status()
        order = resp.json()
        return JsonResponse({'id': order['id']})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --- VISTA 1: CREA EL USUARIO Y SALTA A LA CONTRASEÑA ---
@login_required
def crear_secretaria(request):
    if not hasattr(request.user, 'perfil_medico'):
        messages.error(request, "Acceso denegado.")
        return redirect('home')

    medico_actual = request.user.perfil_medico
    secretarias_actuales = Secretaria.objects.filter(medico=medico_actual)
    
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
                            is_active=True
                        )
                        user.set_unusable_password()
                        user.save()

                        Secretaria.objects.create(
                            usuario=user,
                            medico=medico_actual,
                            telefono=request.POST.get('telefono') # Asegúrate de capturar el telf aquí
                        )
                        
                        from django.contrib.auth.models import Group
                        grupo, _ = Group.objects.get_or_create(name='Secretarias')
                        user.groups.add(grupo)

                    try:
                        enviar_correo_activacion(request, user)
                        messages.success(request, f"Secretaria {user.first_name} registrada y correo enviado.")
                    except Exception as mail_error:
                        messages.warning(request, f"Secretaria creada, pero el correo falló: {mail_error}")
                    
                    return redirect('crear_secretaria') 

                except Exception as e:
                    messages.error(request, f"Error en la base de datos: {e}")
    else:
        form = SecretariaRegistroForm()

    return render(request, 'crear_secretaria.html', {
        'form': form,
        'secretarias': secretarias_actuales
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

def asignar_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            user = form.save()
            
            # Protección: solo asigna MEDICO si el usuario es nuevo o PACIENTE
            if user.role in [None, 'PACIENTE', '']:
                 user.role = 'MEDICO'
                 user.save()
            
            messages.success(request, "Contraseña establecida. Ya puede iniciar sesión.")
            return redirect('login')
    else:
        form = SetPasswordForm(user)
    
    return render(request, 'asignar_password.html', {'form': form, 'user_obj': user})

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
    
def probar_email(request):
    try:
        asunto = 'Prueba de Conexión MediSys Pro'
        mensaje = 'Si recibes esto, la configuración de Gmail en SaludDigital es correcta. 🚀'
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

@require_POST
@transaction.atomic
def confirmar_pago(request):
    """
    El frontend llama a esta vista (POST + JSON) con el orderID aprobado por PayPal.
    El servidor captura el pago en PayPal y SOLO si es exitoso crea el User y el Medico.
    """
    from django.http import JsonResponse
    from medico.models import Medico, Especialidad

    User = get_user_model()

    # 1. Leer datos de sesión — si no hay sesión no hacemos nada
    datos = request.session.get('datos_registro_pendiente')
    if not datos:
        return JsonResponse({'error': 'Sesión de registro expirada. Vuelva a registrarse.'}, status=400)

    # 2. Leer el orderID enviado por el frontend
    import json
    try:
        body = json.loads(request.body)
        order_id = body.get('orderID')
    except (json.JSONDecodeError, AttributeError):
        order_id = None

    if not order_id:
        return JsonResponse({'error': 'No se recibió el ID de la orden de pago.'}, status=400)

    # 3. Capturar el pago en PayPal (SERVER-SIDE) — esto verifica que el dinero fue cobrado
    try:
        token = _paypal_access_token()
        capture_url = f'{_paypal_base_url()}/v2/checkout/orders/{order_id}/capture'
        resp = http_requests.post(
            capture_url,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            timeout=20,
        )
        resp.raise_for_status()
        capture_data = resp.json()
    except Exception as e:
        return JsonResponse({'error': f'No se pudo verificar el pago con PayPal: {e}'}, status=502)

    # 4. Confirmar que el estado de la captura es COMPLETED
    capture_status = capture_data.get('status')
    if capture_status != 'COMPLETED':
        return JsonResponse(
            {'error': f'El pago no fue completado (estado: {capture_status}).'},
            status=400
        )

    # 5. Pago verificado — ahora sí creamos el usuario y el perfil médico
    try:
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
        especialidad_obj = Especialidad.objects.get(id=especialidad_id) if especialidad_id else None

        medico_obj = Medico.objects.create(
            usuario=user,
            especialidad=especialidad_obj,
            registro_senescyt=datos.get('registro_senescyt', ''),
            telefono_consultorio=datos.get('telefono_consultorio', ''),
            direccion_consultorio=datos.get('direccion_consultorio', ''),
        )

        # 6. Enviar correo de activación
        try:
            enviar_correo_activacion(request, user)
        except Exception as email_error:
            print(f"[EMAIL ERROR] No se pudo enviar correo de activación: {email_error}")

        # 7. Generar factura electrónica SRI (no bloqueante)
        try:
            from facturacion.services.sri import SriService
            from decimal import Decimal
            SriService().crear_factura_pago(medico_obj, Decimal('50.00'))
        except Exception as factura_error:
            # La factura falla silenciosamente; el admin puede reenviar desde el panel
            print(f"[FACTURACIÓN] Error al generar factura: {factura_error}")

        # 8. Guardar email para mostrarlo en la página de éxito, luego limpiar sesión
        email_registrado = datos.get('email', '')
        logout(request)
        request.session['registro_email'] = email_registrado

        return JsonResponse({'redirect': '/registro-exitoso/'})

    except Exception as e:
        # Si falla la creación del usuario después de cobrar, retornamos el error
        # pero el pago ya fue capturado — el admin debe revisarlo
        return JsonResponse({'error': f'Pago cobrado pero error al crear la cuenta: {e}'}, status=500)


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