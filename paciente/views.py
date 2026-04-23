from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required

from .models import Paciente
from .forms import PacienteForm
from historia.models import HistoriaClinica
from users.decorators import medico_required
from django.db.models import Q

@login_required
def listar_pacientes(request):
    # 1. Identificamos al médico/clínica para el contexto (opcional para filtros futuros)
    if request.user.role == 'SECRETARIA':
        medico_id = request.user.perfil_secretaria.medico_id
    else:
        medico_id = request.user.perfil_medico.id

    # 2. CAMBIO CLAVE: Quitamos el filtro obligatorio de citas.
    # Ahora buscamos TODOS los pacientes para que el nuevo aparezca de inmediato.
    # Usamos order_by('-id') para que el recién creado sea el PRIMERO en la lista.
    pacientes = Paciente.objects.all().select_related('usuario').order_by('-id')

    # 3. OPCIONAL: Si quieres mantener el buscador (muy recomendado)
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