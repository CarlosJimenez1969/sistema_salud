from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from .models import Paciente
from .forms import PacienteForm

@login_required
def listar_pacientes(request):
    # Traemos todos los pacientes del sistema
    pacientes = Paciente.objects.all()
    return render(request, 'listar_pacientes.html', {'pacientes': pacientes})

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