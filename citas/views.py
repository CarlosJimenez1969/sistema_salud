from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime, timedelta, date, time
from .models import Cita
from medico.models import Medico, Especialidad, Pais, Ciudad
from paciente.models import Paciente, Mascota
from django.utils import timezone
from .forms import CitaForm
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

import ssl
from django.core.mail import get_connection, send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings

# 1. Pantalla para buscar médicos por especialidad y ubicación
def buscar_medico(request):
    especialidades = Especialidad.objects.all().order_by('nombre')
    paises         = Pais.objects.all()

    especialidad_id = request.GET.get('especialidad')
    pais_id         = request.GET.get('pais', '').strip()
    ciudad_id       = request.GET.get('ciudad', '').strip()
    sector          = request.GET.get('sector', '').strip()

    medicos = None
    busqueda_activa = any([especialidad_id, pais_id, ciudad_id, sector])

    # Ciudades del país seleccionado (para repoblar el combo en el GET)
    ciudades_filtro = Ciudad.objects.filter(pais_id=pais_id) if pais_id else Ciudad.objects.none()

    if busqueda_activa:
        medicos = Medico.objects.select_related('usuario', 'especialidad').all()
        if especialidad_id:
            medicos = medicos.filter(especialidad_id=especialidad_id)
        if pais_id:
            medicos = medicos.filter(pais__icontains=Pais.objects.get(id=pais_id).nombre) if Pais.objects.filter(id=pais_id).exists() else medicos
        if ciudad_id:
            medicos = medicos.filter(ciudad__icontains=Ciudad.objects.get(id=ciudad_id).nombre) if Ciudad.objects.filter(id=ciudad_id).exists() else medicos
        if sector:
            medicos = medicos.filter(sector=sector)

    sectores = [('NORTE','Norte'), ('CENTRO','Centro'), ('SUR','Sur'), ('VALLES','Valles'), ('OTRO','Otro')]

    return render(request, 'buscar_medico.html', {
        'especialidades': especialidades,
        'paises': paises,
        'ciudades_filtro': ciudades_filtro,
        'medicos': medicos,
        'sectores': sectores,
        'busqueda_activa': busqueda_activa,
        'filtros': {'especialidad_id': especialidad_id, 'pais_id': pais_id, 'ciudad_id': ciudad_id, 'sector': sector},
    })

# 2. Pantalla Gráfica de Turnos (La Lógica Maestra)
@login_required
def reservar_cita(request, medico_id):
    # --- BLOQUEO DE SEGURIDAD PARA SECRETARIAS ---
    es_secretaria = getattr(request.user, 'role', '') == 'SECRETARIA'
    
    if es_secretaria:
        # Forzamos que el médico sea ÚNICAMENTE el vinculado a ella
        medico = get_object_or_404(Medico, mis_secretarias__usuario=request.user)
    else:
        medico = get_object_or_404(Medico, id=medico_id)

    es_medico = hasattr(request.user, 'perfil_medico')
    es_administrativo = (es_secretaria or es_medico)

    # 1. Obtener Paciente y Fecha
    paciente_seleccionado_id = request.GET.get('paciente_id')
    fecha_str = request.GET.get('fecha')
    
    if fecha_str:
        fecha_seleccionada = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    else:
        fecha_seleccionada = date.today()

    # 2. OBTENER CITAS DEL MÉDICO
    citas_medico = Cita.objects.filter(
        medico=medico,
        fecha=fecha_seleccionada,
        estado='P'
    ).select_related('paciente__usuario')

    dict_ocupados_medico = {
        c.hora.strftime('%H:%M'): {'id': c.paciente.id, 'nombre': c.paciente.usuario.get_full_name()} 
        for c in citas_medico
    }

    # 3. CITAS DEL PACIENTE SELECCIONADO
    lista_horas_paciente = []
    if paciente_seleccionado_id:
        citas_p = Cita.objects.filter(
            paciente_id=paciente_seleccionado_id,
            fecha=fecha_seleccionada,
            estado='P'
        ).values_list('hora', flat=True)
        lista_horas_paciente = [h.strftime('%H:%M') for h in citas_p]

    # 4. LÓGICA DE TIEMPO ACTUAL Y GENERACIÓN DE HORARIOS
    ahora = timezone.localtime(timezone.now())
    hoy = date.today()
    minutos_ahora = (ahora.hour * 60) + ahora.minute

    # --- CORRECCIÓN: Horarios por defecto si están vacíos ---
    h_inicio = medico.hora_inicio or time(8, 0)  # 8:00 AM si es None
    h_fin = medico.hora_fin or time(18, 0)      # 6:00 PM si es None

    horarios = []
    hora_actual = h_inicio
    
    # El bucle ahora usa nuestras variables de respaldo
    while hora_actual < h_fin:
        hora_str = hora_actual.strftime('%H:%M')
        info_cita = dict_ocupados_medico.get(hora_str)
        minutos_slot = (hora_actual.hour * 60) + hora_actual.minute
        
        esta_ocupado_cita = (hora_str in dict_ocupados_medico) or (hora_str in lista_horas_paciente)
        es_pasada = (fecha_seleccionada == hoy) and (minutos_slot < minutos_ahora)

        horarios.append({
            'hora': hora_actual,
            'ocupado': esta_ocupado_cita or es_pasada,
            'paciente_nombre': info_cita['nombre'] if info_cita else None,
            'paciente_id': info_cita['id'] if info_cita else None,
            'conflicto_paciente': hora_str in lista_horas_paciente,
            'es_pasada': es_pasada 
        })
        
        intervalo = medico.intervalo_minutos or 30
        dt_aux = datetime.combine(date.today(), hora_actual) + timedelta(minutes=intervalo)
        hora_actual = dt_aux.time()

    # ¿Es veterinario?
    es_veterinario = medico.especialidad and medico.especialidad.nombre.lower() == 'veterinaria'

    # --- Lógica de POST ---
    if request.method == 'POST':
        hora_post   = request.POST.get('hora')
        p_id        = request.POST.get('paciente_id') or paciente_seleccionado_id
        mascota_id  = request.POST.get('mascota_id') or None

        if not hora_post:
            messages.error(request, "Debe seleccionar una hora.")
        elif es_veterinario and es_administrativo and not mascota_id:
            messages.error(request, "Debe seleccionar la mascota para la cita veterinaria.")
        elif es_veterinario and not es_administrativo and not mascota_id:
            messages.error(request, "Debe seleccionar la mascota para la cita veterinaria.")
        else:
            try:
                mascota = None
                if es_veterinario and mascota_id:
                    mascota = get_object_or_404(Mascota, id=mascota_id, activo=True)
                    paciente = mascota.propietario  # El dueño es el paciente
                else:
                    paciente = get_object_or_404(Paciente, id=p_id) if es_administrativo else request.user.perfil_paciente

                Cita.objects.create(
                    medico=medico,
                    paciente=paciente,
                    mascota=mascota,
                    fecha=fecha_seleccionada,
                    hora=hora_post,
                    estado='P'
                )
                quien = mascota.nombre if mascota else paciente
                messages.success(request, f'Cita agendada con el Dr. {medico.usuario.last_name} para {quien}')
                return redirect('dashboard_secretaria' if es_secretaria else 'home')
            except Exception as e:
                print(f"[RESERVAR_CITA ERROR] {e}")
                messages.error(request, "No se pudo agendar la cita. Verifica los datos e intenta nuevamente.")

    # Para veterinarios el "paciente" en el combo es la MASCOTA
    lista_mascotas = Mascota.objects.none()
    if es_administrativo:
        if es_veterinario:
            lista_mascotas = (
                Mascota.objects.filter(activo=True)
                .select_related('propietario__usuario')
                .order_by('nombre')
            )
            lista_pacientes = Paciente.objects.none()
        else:
            base_qs = Paciente.objects.filter(
                usuario__perfil_medico__isnull=True,
                usuario__perfil_secretaria__isnull=True,
            )
            lista_pacientes = (
                base_qs.filter(citas__medico=medico)
                .select_related('usuario')
                .distinct()
                .order_by('usuario__last_name')
            )
    else:
        lista_pacientes = Paciente.objects.none()

    # Lista de mascotas del paciente actual (si es veterinario)
    mis_mascotas = []
    if es_veterinario:
        if not es_administrativo and hasattr(request.user, 'perfil_paciente'):
            mis_mascotas = request.user.perfil_paciente.mascotas.filter(activo=True)
        elif es_administrativo and paciente_seleccionado_id:
            # Si la secretaria/médico seleccionó un paciente, mostrar sus mascotas
            try:
                p = Paciente.objects.get(id=paciente_seleccionado_id)
                mis_mascotas = p.mascotas.filter(activo=True)
            except Paciente.DoesNotExist:
                pass

    return render(request, 'reservar_cita.html', {
        'medico': medico,
        'horarios': horarios,
        'fecha_seleccionada': fecha_seleccionada,
        'lista_pacientes': lista_pacientes,
        'lista_mascotas': lista_mascotas,
        'es_veterinario': es_veterinario,
        'mis_mascotas': mis_mascotas,
        'es_administrativo': es_administrativo,
        'paciente_seleccionado_id': paciente_seleccionado_id,
        'dia_anterior': fecha_seleccionada - timedelta(days=1) if fecha_seleccionada > hoy else None,
        'dia_siguiente': fecha_seleccionada + timedelta(days=1),
    })

@login_required
def ver_agenda(request):
    # Verificación de seguridad: ¿Es médico?
    try:
        medico = request.user.perfil_medico
    except:
        return render(request, 'error.html', {'mensaje': 'Solo los médicos tienen agenda.'})

    # Fecha: Por defecto HOY, o la que elija en el calendario
    fecha_str = request.GET.get('fecha')
    if fecha_str:
        fecha_agenda = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    else:
        fecha_agenda = date.today()

    # Filtramos las citas
    citas = Cita.objects.filter(
        medico=medico,
        fecha=fecha_agenda
    ).order_by('hora')

    # Lógica para cancelar citas desde la misma agenda (POST)
    if request.method == 'POST':
        cita_id = request.POST.get('cita_id')
        accion = request.POST.get('accion')
        cita = get_object_or_404(Cita, id=cita_id, medico=medico)
        
        if accion == 'cancelar':
            cita.estado = 'C'
            cita.save()
            messages.warning(request, 'Cita cancelada.')
        elif accion == 'finalizar':
            cita.estado = 'A'
            cita.save()
            messages.success(request, 'Cita finalizada.')
            
        return redirect(f'/citas/agenda/?fecha={fecha_agenda}')

    return render(request, 'ver_agenda.html', {
        'citas': citas,
        'fecha_agenda': fecha_agenda,
        'hoy': date.today()
    })

@login_required
def dashboard_secretaria(request):
    # 1. Obtener el perfil de secretaria y su médico vinculado
    try:
        perfil_sec = request.user.perfil_secretaria 
        medico_vinculado = perfil_sec.medico
    except AttributeError:
        messages.error(request, "No tienes un perfil de secretaria asignado.")
        return redirect('home')

    from django.utils import timezone
    hoy = timezone.now().date()
    
    # 2. Lógica del Buscador Preventivo (Opcional, pero recomendada)
    query = request.GET.get('buscar_paciente', '').strip()
    resultado_busqueda = None
    if query:
        resultado_busqueda = Cita.objects.filter(
            medico=medico_vinculado,
            fecha=hoy,
            paciente__usuario__cedula__icontains=query
        ).first()

    # 3. Obtener Citas de hoy con optimización (prefetch_related para las historias)
    # Usamos prefetch_related('paciente__historias') para que el template 
    # sepa si hay historias sin hacer una consulta nueva por cada fila.
    citas_hoy = Cita.objects.filter(
        medico=medico_vinculado, 
        fecha=hoy
    ).select_related('paciente__usuario').prefetch_related('paciente__historias').order_by('hora')

    es_veterinario = (
        medico_vinculado.especialidad
        and 'veterin' in medico_vinculado.especialidad.nombre.lower()
    )

    context = {
        'medico': medico_vinculado,
        'secretaria': perfil_sec,
        'citas_hoy': citas_hoy,
        'total_citas': citas_hoy.count(),
        'query': query,
        'resultado_busqueda': resultado_busqueda,
        'es_veterinario': es_veterinario,
    }

    return render(request, 'dashboard_secretaria.html', context)

def _cita_del_usuario(request, cita_id):
    """Obtiene una Cita validando que pertenezca al médico/secretaria/admin del usuario logueado."""
    role = getattr(request.user, 'role', '')
    if role == 'ADMIN':
        return get_object_or_404(Cita, id=cita_id)
    if role == 'MEDICO' and hasattr(request.user, 'perfil_medico'):
        return get_object_or_404(Cita, id=cita_id, medico=request.user.perfil_medico)
    if role == 'SECRETARIA' and hasattr(request.user, 'perfil_secretaria'):
        return get_object_or_404(Cita, id=cita_id, medico=request.user.perfil_secretaria.medico)
    from django.core.exceptions import PermissionDenied
    raise PermissionDenied


@login_required
def cambiar_estado_cita(request, cita_id, nuevo_estado):
    if request.method == 'POST':
        cita = _cita_del_usuario(request, cita_id)

        estado_map = {'COMPLETADA': 'A', 'CANCELADA': 'C', 'A': 'A', 'C': 'C'}
        if nuevo_estado in estado_map:
            cita.estado = estado_map[nuevo_estado]
            cita.save()

            if cita.estado == 'A':
                messages.success(request, f"Cita de {cita.paciente.usuario.first_name} marcada como ATENDIDA.")
            else:
                messages.warning(request, f"Cita de {cita.paciente.usuario.first_name} ha sido CANCELADA.")

    # Redirect seguro según rol (evita open redirect vía Referer)
    role = getattr(request.user, 'role', '')
    if role == 'SECRETARIA':
        return redirect('dashboard_secretaria')
    return redirect('home')


@login_required
def editar_cita(request, cita_id):
    cita = _cita_del_usuario(request, cita_id)

    if request.method == 'POST':
        form = CitaForm(request.POST, instance=cita)
        if form.is_valid():
            form.save()
            return redirect('dashboard_secretaria')
    else:
        form = CitaForm(instance=cita)

    return render(request, 'citas/editar_cita.html', {'form': form, 'cita': cita})


@login_required
def eliminar_cita(request, cita_id):
    if request.method == 'POST':
        cita = _cita_del_usuario(request, cita_id)
        nombre_paciente = cita.paciente.usuario.get_full_name()
        cita.delete()
        messages.error(request, f"La cita de {nombre_paciente} ha sido eliminada permanentemente.")
    
    return redirect('dashboard_secretaria')

def enviar_correo_activacion(request, user):
    """
    Genera un token de seguridad y envía el enlace de activación 
    según el rol del usuario (Médico o Secretaria).
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    import ssl

    # 1. Generar los datos de seguridad
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # 2. Construir el enlace
    link = f"http://{request.get_host()}/reset/{uid}/{token}/"

    # 3. Detectar el rol para personalizar el mensaje
    # Usamos .upper() por si acaso el rol está en minúsculas
    rol_nombre = "Médico" if str(user.role).upper() == 'MEDICO' else "Secretaria"

    asunto = f"Bienvenida a MediSys Pro - Activa tu cuenta de {rol_nombre}"
    
    mensaje = (
        f"Hola {user.first_name},\n\n"
        f"Se ha creado tu perfil de {rol_nombre.lower()} en el sistema.\n"
        f"Para activar tu cuenta y configurar tu contraseña, haz clic en el siguiente enlace:\n\n"
        f"{link}\n\n"
        f"Si no solicitaste esta cuenta, por favor ignora este mensaje."
    )

    # 4. Enviar el correo usando la configuración de settings.py
    # Mantenemos tu lógica de bypass SSL por si tu entorno local lo requiere
    try:
        context = ssl._create_unverified_context()
        connection = get_connection(
            backend=settings.EMAIL_BACKEND,
            use_tls=settings.EMAIL_USE_TLS,
            ssl_context=context,
            timeout=15,
        )

        send_mail(
            asunto,
            mensaje,
            settings.EMAIL_HOST_USER,
            [user.email],
            connection=connection,
            fail_silently=False,
        )
        print(f"DEBUG: Correo de {rol_nombre} enviado exitosamente a {user.email}")
    except Exception as e:
        print(f"ERR: Error físico enviando correo: {e}")
        raise e # Re-lanzamos para que confirmar_pago vea el error
    
@login_required
def detalle_cita(request, cita_id):
    cita = _cita_del_usuario(request, cita_id)
    return render(request, 'detalle_cita_modal.html', {'cita': cita})