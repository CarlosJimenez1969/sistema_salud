from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login

from citas.models import Cita
from .forms import RegistroMedicoForm, SecretariaRegistroForm
from .models import User
from django.db.models import Count
from django.db.models.functions import TruncMonth
from medico.models import Medico, Especialidad
from paciente.models import Paciente
from django.contrib import messages

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import Group # Importar Grupos



@login_required
def home(request):
    # --- LOGICA PARA PACIENTES (MIS CITAS) ---
    citas_proximas = []
    if request.user.role == 'PACIENTE':
        try:
            paciente = request.user.perfil_paciente
            citas_proximas = Cita.objects.filter(
                paciente=paciente,
                fecha__gte=date.today(),
                estado='PENDIENTE'
            ).order_by('fecha', 'hora')
        except:
            pass

    # --- LOGICA PARA MÉDICOS / ADMINS (DASHBOARD) ---
    # Variables vacías por defecto
    total_pacientes = 0
    total_medicos = 0
    citas_totales = 0
    grafico_meses = []
    grafico_cantidades = []

    if request.user.role in ['ADMIN', 'MEDICO']:
        # 1. Contadores Simples (Tarjetas)
        total_pacientes = Paciente.objects.count()
        total_medicos = Medico.objects.count()
        citas_totales = Cita.objects.count()
        
        # 2. Datos para el Gráfico (Citas por Mes)
        # Esto agrupa las citas por mes y las cuenta. Magia de Django.
        datos_grafico = Cita.objects.annotate(
            mes=TruncMonth('fecha')
        ).values('mes').annotate(
            cantidad=Count('id')
        ).order_by('mes')

        # Separamos los datos para enviarlos a JavaScript
        for d in datos_grafico:
            if d['mes']: # Solo si la fecha es válida
                grafico_meses.append(d['mes'].strftime("%B")) # Nombre del mes (Enero, Febrero...)
                grafico_cantidades.append(d['cantidad'])

    return render(request, 'home.html', {
        'citas_proximas': citas_proximas,
        # Datos del Dashboard
        'total_pacientes': total_pacientes,
        'total_medicos': total_medicos,
        'citas_totales': citas_totales,
        # Listas para los gráficos (chart.js)
        'grafico_meses': grafico_meses, 
        'grafico_cantidades': grafico_cantidades,
    })

# Vista 1: Formulario de Registro
def registro_medico(request):
    if request.method == 'POST':
        form = RegistroMedicoForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Logueamos al usuario automáticamente pero lo enviamos a pagar
            login(request, user)
            return redirect('pasarela_pago')
    else:
        form = RegistroMedicoForm()
    return render(request, 'registro_medico.html', {'form': form})

# Vista 2: Pantalla de Pago Simulada
def pasarela_pago(request):
    if request.method == 'POST':
        # Cuando hace clic en "Pagar", simulamos el éxito
        user = request.user
        user.pago_realizado = True
        user.save()
        return redirect('home') # Lo enviamos al Dashboard
        
    return render(request, 'pago.html')

@login_required
def crear_secretaria(request):
    if not hasattr(request.user, 'perfil_medico'):
        messages.error(request, "Acceso denegado.")
        return redirect('home')

    if request.method == 'POST':
        form = SecretariaRegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            # 1. Creamos usuario SIN contraseña activa
            user.set_unusable_password()
            user.is_staff = True  # Permiso básico
            user.save()
            
            # 2. Asignar al Grupo "Secretaria" (Para controlar qué ve después)
            grupo_secretaria, created = Group.objects.get_or_create(name='Secretarias')
            user.groups.add(grupo_secretaria)

            # 3. Generar el Link de "Crear Contraseña"
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Construimos la URL completa (ej: https://tusitio.com/reset/...)
            link = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )

            # 4. Enviar el Correo
            asunto = f"Bienvenido/a al equipo del Dr. {request.user.last_name}"
            mensaje = f"""
            Hola {user.first_name},
            
            El Dr. {request.user.last_name} te ha registrado como asistente en el sistema MediSys.
            
            Para activar tu cuenta y configurar tu contraseña, haz clic aquí:
            {link}
            
            Atentamente,
            El Equipo de Soporte
            """
            
            try:
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, f'Invitación enviada a {user.email}')
            except Exception as e:
                messages.warning(request, f'Usuario creado, pero falló el envío del correo: {e}')

            return redirect('home')
    else:
        form = SecretariaRegistroForm()

    return render(request, 'crear_secretaria.html', {'form': form})