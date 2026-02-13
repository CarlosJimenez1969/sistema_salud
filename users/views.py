from datetime import date
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
from django.contrib.auth.models import User, Group # Importar Grupos

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import SetPasswordForm

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

# --- VISTA 1: CREA EL USUARIO Y SALTA A LA CONTRASEÑA ---
@login_required
def crear_secretaria(request):
    # Seguridad: Solo médico
    if not hasattr(request.user, 'perfil_medico'):
        messages.error(request, "Acceso denegado.")
        return redirect('home')

    if request.method == 'POST':
        form = SecretariaRegistroForm(request.POST)
        if form.is_valid():
            # 1. Guardar usuario básico
            user = form.save(commit=False)
            user.set_unusable_password() # Sin clave por ahora
            user.is_staff = True 
            user.save()
            
            # 2. Asignar grupo
            grupo, _ = Group.objects.get_or_create(name='Secretarias')
            user.groups.add(grupo)

            # 3. ¡AQUÍ ESTÁ EL CAMBIO! Redirigir a la vista de contraseña
            return redirect('asignar_password', user_id=user.id)
            
    else:
        form = SecretariaRegistroForm()

    return render(request, 'crear_secretaria.html', {'form': form})


# --- VISTA 2: PANTALLA PARA PONER LA CLAVE ---
@login_required
def asignar_password(request, user_id):
    # Buscamos al usuario que acabamos de crear
    usuario_nuevo = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        # Formulario especial de Django para poner claves
        form = SetPasswordForm(usuario_nuevo, request.POST)
        if form.is_valid():
            form.save() # Guarda y encripta
            messages.success(request, f"¡Usuario {usuario_nuevo.username} listo! Prueba ingresar ahora.")
            return redirect('login') # Mandamos al login para probar
    else:
        form = SetPasswordForm(usuario_nuevo)

    return render(request, 'asignar_password.html', {
        'form': form,
        'usuario_nuevo': usuario_nuevo
    })