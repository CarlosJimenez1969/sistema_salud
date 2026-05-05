from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages

from .models import Paciente, Mascota
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
def resumen_paciente_rapido(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    role = getattr(request.user, 'role', '')

    # Validar acceso: admin ve todo, médico/secretaria solo si tienen relación
    from citas.models import Cita
    if role == 'ADMIN':
        pass
    elif role == 'MEDICO' and hasattr(request.user, 'perfil_medico'):
        if not Cita.objects.filter(medico=request.user.perfil_medico, paciente=paciente).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
    elif role == 'SECRETARIA' and hasattr(request.user, 'perfil_secretaria'):
        if not Cita.objects.filter(medico=request.user.perfil_secretaria.medico, paciente=paciente).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
    else:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

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
            messages.success(request, f'¡Bienvenido/a {user.first_name}! Tu cuenta fue creada. Ahora puedes buscar un médico y reservar tu cita.')
            return redirect('buscar_medico')
    else:
        form = RegistroPacienteForm()

    return render(request, 'registro_paciente.html', {'form': form})


# ─── CRUD de Mascotas ──────────────────────────────────────────────────────────

def _paciente_del_usuario(request):
    """Devuelve el Paciente del usuario logueado o None."""
    if hasattr(request.user, 'perfil_paciente'):
        return request.user.perfil_paciente
    return None


@login_required
def listar_mascotas(request):
    paciente = _paciente_del_usuario(request)
    if not paciente:
        messages.error(request, "Debes registrarte como paciente para gestionar mascotas.")
        return redirect('home')
    mascotas = paciente.mascotas.filter(activo=True).order_by('-creado')
    return render(request, 'mascotas/listar.html', {'mascotas': mascotas})


@login_required
def crear_mascota(request):
    paciente = _paciente_del_usuario(request)
    if not paciente:
        messages.error(request, "Debes registrarte como paciente para registrar mascotas.")
        return redirect('home')

    if request.method == 'POST':
        m = Mascota(propietario=paciente)
        m.nombre           = request.POST.get('nombre', '').strip()
        m.especie          = request.POST.get('especie', '')
        m.raza             = request.POST.get('raza', '').strip()
        m.sexo             = request.POST.get('sexo', '')
        m.color            = request.POST.get('color', '').strip()
        fn                 = request.POST.get('fecha_nacimiento', '')
        m.fecha_nacimiento = fn or None
        peso               = request.POST.get('peso', '').strip()
        m.peso             = peso or None
        m.esterilizado     = bool(request.POST.get('esterilizado'))
        m.chip_id          = request.POST.get('chip_id', '').strip()
        m.alergias         = request.POST.get('alergias', '').strip()
        m.enfermedades_cronicas = request.POST.get('enfermedades_cronicas', '').strip()
        m.notas            = request.POST.get('notas', '').strip()
        if 'foto' in request.FILES:
            m.foto = request.FILES['foto']

        if not m.nombre or not m.especie:
            messages.error(request, "Nombre y especie son obligatorios.")
            return render(request, 'mascotas/crear.html', {'datos': request.POST, 'especies': Mascota.ESPECIES})

        m.save()
        messages.success(request, f"Mascota '{m.nombre}' registrada correctamente.")
        return redirect('listar_mascotas')

    return render(request, 'mascotas/crear.html', {'especies': Mascota.ESPECIES})


@login_required
def editar_mascota(request, mascota_id):
    paciente = _paciente_del_usuario(request)
    mascota = get_object_or_404(Mascota, id=mascota_id, propietario=paciente)

    if request.method == 'POST':
        mascota.nombre           = request.POST.get('nombre', '').strip()
        mascota.especie          = request.POST.get('especie', '')
        mascota.raza             = request.POST.get('raza', '').strip()
        mascota.sexo             = request.POST.get('sexo', '')
        mascota.color            = request.POST.get('color', '').strip()
        fn                       = request.POST.get('fecha_nacimiento', '')
        mascota.fecha_nacimiento = fn or None
        peso                     = request.POST.get('peso', '').strip()
        mascota.peso             = peso or None
        mascota.esterilizado     = bool(request.POST.get('esterilizado'))
        mascota.chip_id          = request.POST.get('chip_id', '').strip()
        mascota.alergias         = request.POST.get('alergias', '').strip()
        mascota.enfermedades_cronicas = request.POST.get('enfermedades_cronicas', '').strip()
        mascota.notas            = request.POST.get('notas', '').strip()
        if 'foto' in request.FILES:
            mascota.foto = request.FILES['foto']
        mascota.save()
        messages.success(request, f"'{mascota.nombre}' actualizada correctamente.")
        return redirect('listar_mascotas')

    return render(request, 'mascotas/crear.html', {
        'datos': {
            'nombre': mascota.nombre, 'especie': mascota.especie, 'raza': mascota.raza,
            'sexo': mascota.sexo, 'color': mascota.color,
            'fecha_nacimiento': mascota.fecha_nacimiento, 'peso': mascota.peso,
            'esterilizado': mascota.esterilizado, 'chip_id': mascota.chip_id,
            'alergias': mascota.alergias, 'enfermedades_cronicas': mascota.enfermedades_cronicas,
            'notas': mascota.notas,
        },
        'mascota': mascota,
        'especies': Mascota.ESPECIES,
    })


@login_required
def eliminar_mascota(request, mascota_id):
    paciente = _paciente_del_usuario(request)
    mascota = get_object_or_404(Mascota, id=mascota_id, propietario=paciente)
    if request.method == 'POST':
        mascota.activo = False
        mascota.save()
        messages.warning(request, f"'{mascota.nombre}' fue eliminada de tus mascotas.")
    return redirect('listar_mascotas')