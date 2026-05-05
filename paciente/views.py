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

    es_vet = _es_veterinario(request)

    # Solo pacientes con rol PACIENTE (excluye usuarios médicos/secretarias/admins)
    # Para veterinarios no aplicamos exclusión estricta por perfil (un usuario puede ser ambos)
    # Para no-veterinarios sí excluimos usuarios médicos/secretarias
    if es_vet:
        from paciente.models import Mascota
        ids_con_mascotas = set(Mascota.objects.values_list('propietario_id', flat=True))

        if request.user.role == 'ADMIN':
            pacientes = Paciente.objects.all().select_related('usuario').order_by('-id')
        else:
            medico = request.user.perfil_medico if request.user.role == 'MEDICO' else request.user.perfil_secretaria.medico
            ids_con_citas = set(Paciente.objects.filter(citas__medico=medico).values_list('id', flat=True))
            ids_finales   = ids_con_mascotas | ids_con_citas
            pacientes = (
                Paciente.objects.filter(id__in=ids_finales)
                .select_related('usuario')
                .order_by('-id')
            )
    else:
        base_qs = Paciente.objects.filter(
            usuario__perfil_medico__isnull=True,
            usuario__perfil_secretaria__isnull=True,
        )
        if request.user.role == 'ADMIN':
            pacientes = base_qs.select_related('usuario').order_by('-id')
        elif request.user.role == 'SECRETARIA':
            medico = request.user.perfil_secretaria.medico
            pacientes = base_qs.filter(
                citas__medico=medico
            ).select_related('usuario').distinct().order_by('-id')
        else:
            medico = request.user.perfil_medico
            pacientes = base_qs.filter(
                citas__medico=medico
            ).select_related('usuario').distinct().order_by('-id')

    query = request.GET.get('q')
    if query:
        pacientes = pacientes.filter(
            Q(usuario__first_name__icontains=query) |
            Q(usuario__last_name__icontains=query) |
            Q(usuario__cedula__icontains=query) |
            Q(mascotas__nombre__icontains=query)
        ).distinct()

    if es_vet:
        # Para veterinarios, mostrar también las mascotas
        pacientes = pacientes.prefetch_related('mascotas')

    return render(request, 'listar_pacientes.html', {
        'pacientes': pacientes,
        'query': query,
        'es_veterinario': es_vet
    })

def _es_veterinario(request):
    """Detecta si el usuario logueado es veterinario o secretaria de un veterinario."""
    role = getattr(request.user, 'role', '')
    medico = None
    if role == 'MEDICO' and hasattr(request.user, 'perfil_medico'):
        medico = request.user.perfil_medico
    elif role == 'SECRETARIA' and hasattr(request.user, 'perfil_secretaria'):
        medico = request.user.perfil_secretaria.medico
    if not medico or not medico.especialidad:
        return False
    return 'veterin' in medico.especialidad.nombre.lower()


@login_required
def crear_paciente(request):
    # Si es veterinario, redirigir al formulario de registro de mascota+dueño
    if _es_veterinario(request):
        return redirect('crear_paciente_veterinario')

    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_pacientes')
    else:
        form = PacienteForm()

    return render(request, 'crear_paciente.html', {'form': form})


@login_required
def crear_paciente_veterinario(request):
    """Registro veterinario: dueño humano + mascota en un solo formulario."""
    if not _es_veterinario(request):
        messages.error(request, "Solo veterinarios pueden registrar mascotas como pacientes.")
        return redirect('listar_pacientes')

    from users.models import User
    if request.method == 'POST':
        # Datos del dueño
        dueno_first    = request.POST.get('dueno_first_name', '').strip()
        dueno_last     = request.POST.get('dueno_last_name', '').strip()
        dueno_cedula   = request.POST.get('dueno_cedula', '').strip()
        dueno_email    = request.POST.get('dueno_email', '').strip()
        dueno_telefono = request.POST.get('dueno_telefono', '').strip()
        dueno_direccion= request.POST.get('dueno_direccion', '').strip()

        # Datos de la mascota
        m_nombre   = request.POST.get('mascota_nombre', '').strip()
        m_especie  = request.POST.get('mascota_especie', '')
        m_raza     = request.POST.get('mascota_raza', '').strip()
        m_sexo     = request.POST.get('mascota_sexo', '')
        m_color    = request.POST.get('mascota_color', '').strip()
        m_fn       = request.POST.get('mascota_fecha_nacimiento') or None
        m_peso     = request.POST.get('mascota_peso') or None
        m_chip     = request.POST.get('mascota_chip', '').strip()
        m_alergias = request.POST.get('mascota_alergias', '').strip()
        m_enf      = request.POST.get('mascota_enf', '').strip()
        m_ester    = bool(request.POST.get('mascota_esterilizado'))

        if not all([dueno_first, dueno_last, dueno_cedula, dueno_email, m_nombre, m_especie]):
            messages.error(request, "Faltan datos obligatorios del dueño o de la mascota.")
            return render(request, 'crear_paciente_veterinario.html', {
                'datos': request.POST, 'especies': Mascota.ESPECIES,
            })

        # ¿Existe ya el dueño?
        usuario = User.objects.filter(cedula=dueno_cedula).first() or User.objects.filter(email=dueno_email).first()

        if usuario and usuario.role != 'PACIENTE':
            messages.error(
                request,
                f"La cédula '{dueno_cedula}' o el correo '{dueno_email}' ya están registrados como "
                f"{usuario.role} en el sistema. Por favor use datos diferentes para el dueño."
            )
            return render(request, 'crear_paciente_veterinario.html', {
                'datos': request.POST, 'especies': Mascota.ESPECIES,
            })
        try:
            if usuario:
                paciente, _ = Paciente.objects.get_or_create(usuario=usuario, defaults={
                    'telefono': dueno_telefono, 'direccion': dueno_direccion,
                })
            else:
                usuario = User.objects.create_user(
                    username=dueno_email,
                    email=dueno_email,
                    password=dueno_cedula,
                    first_name=dueno_first,
                    last_name=dueno_last,
                    cedula=dueno_cedula,
                    role=User.Role.PACIENTE,
                )
                paciente = Paciente.objects.create(
                    usuario=usuario, telefono=dueno_telefono, direccion=dueno_direccion,
                )

            mascota = Mascota(
                propietario=paciente,
                nombre=m_nombre, especie=m_especie, raza=m_raza,
                sexo=m_sexo, color=m_color, fecha_nacimiento=m_fn,
                peso=m_peso or None, chip_id=m_chip,
                alergias=m_alergias, enfermedades_cronicas=m_enf,
                esterilizado=m_ester,
            )
            if 'mascota_foto' in request.FILES:
                mascota.foto = request.FILES['mascota_foto']
            mascota.save()

            messages.success(request, f"Mascota '{mascota.nombre}' registrada para {paciente}.")
            return redirect('listar_pacientes')
        except Exception as e:
            print(f"[VET-CREAR ERROR] {e}")
            messages.error(request, f"No se pudo registrar la mascota: {e}")
            return render(request, 'crear_paciente_veterinario.html', {
                'datos': request.POST, 'especies': Mascota.ESPECIES,
            })

    return render(request, 'crear_paciente_veterinario.html', {
        'especies': Mascota.ESPECIES,
    })

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