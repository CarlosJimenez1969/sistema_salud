from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login

from citas.models import Cita
from .forms import RegistroMedicoForm
from .models import User
from django.db.models import Count
from django.db.models.functions import TruncMonth
from medico.models import Medico
from paciente.models import Paciente
# (Asegúrate de tener también Cita y datetime/date importados)

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