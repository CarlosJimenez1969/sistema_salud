from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages

from .models import Paciente
from .forms import PacienteForm, RegistroPacienteForm
from historia.models import HistoriaClinica
from users.decorators import medico_required
from django.db.models import Q

@login_required
def listar_pacientes(request):
    from citas.models import Cita

    # ADMIN ve todos los pacientes; MEDICO y SECRETARIA solo los suyos
    if request.user.role == 'ADMIN':
        pacientes = Paciente.objects.all().select_related('usuario').order_by('-id')
    elif request.user.role == 'SECRETARIA':
        medico = request.user.perfil_secretaria.medico
        pacientes = Paciente.objects.filter(
            citas__medico=medico
        ).select_related('usuario').distinct().order_by('-id')
    else:
        medico = request.user.perfil_medico
        pacientes = Paciente.objects.filter(
            citas__medico=medico
        ).select_related('usuario').distinct().order_by('-id')

    query = request.GET.get('q')
    if query:
        pacientes = pacientes.filter(
            Q(usuario__first_name__icontains=query) |
            Q(usuario__last_name__icontains=query) |
            Q(usuario__cedula__icontains=query)
        ).distinct()

    return render(request, 'listar_pacientes.html', {
        'pacientes': pacientes,
        'query': query
    })

@login_required
def crear_paciente(request):
    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_pacientes') # Al guardar, vuelve a la lista
    else:
        form = PacienteForm()
    
    return render(request, 'crear_paciente.html', {'form': form})

@login_required
def editar_paciente(request, id):
    # Buscamos al paciente por su ID o devolvemos error 404 si no existe
    paciente = get_object_or_404(Paciente, id=id)
    
    if request.method == 'POST':
        # Cargamos el formulario con los datos nuevos (POST) y le decimos que actualice "instance=paciente"
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            return redirect('listar_pacientes')
    else:
        # Si es GET, cargamos el formulario con los datos guardados
        form = PacienteForm(instance=paciente)
    
    # Reutilizamos la plantilla de crear, pero le pasamos un título diferente
    return render(request, 'crear_paciente.html', {'form': form, 'titulo': 'Editar Paciente'})

@login_required
#@medico_required
def resumen_paciente_rapido(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    
    # Obtenemos la última consulta realizada
    ultima_historia = HistoriaClinica.objects.filter(paciente=paciente).order_by('-fecha_atencion').first()
    
    return render(request, 'paciente/resumen_modal.html', {
        'paciente': paciente,
        'h': ultima_historia
    })


def registro_paciente(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistroPacienteForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'¡Bienvenido/a {user.first_name}! Tu cuenta fue creada exitosamente.')
            return redirect('home')
    else:
        form = RegistroPacienteForm()

    return render(request, 'registro_paciente.html', {'form': form})