from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime, timedelta, date, time
from .models import Cita
from medico.models import Medico, Especialidad
from paciente.models import Paciente

# 1. Pantalla para buscar médicos por especialidad
def buscar_medico(request):
    especialidades = Especialidad.objects.all()
    medicos = None
    
    # Si el usuario seleccionó una especialidad
    especialidad_id = request.GET.get('especialidad')
    if especialidad_id:
        medicos = Medico.objects.filter(especialidad_id=especialidad_id)
    
    return render(request, 'buscar_medico.html', {
        'especialidades': especialidades,
        'medicos': medicos
    })

# 2. Pantalla Gráfica de Turnos (La Lógica Maestra)
@login_required
def reservar_cita(request, medico_id):
    medico = get_object_or_404(Medico, id=medico_id)
    
    # --- Lógica para saber si el usuario es Médico ---
    es_medico = hasattr(request.user, 'perfil_medico')
    lista_pacientes = []
    
    # Si es médico, traemos todos los pacientes para que pueda elegir
    if es_medico:
        lista_pacientes = Paciente.objects.all()

    # 1. Obtener la fecha
    fecha_str = request.GET.get('fecha')
    if fecha_str:
        fecha_seleccionada = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    else:
        fecha_seleccionada = date.today()

    # 2. Navegación Día Anterior / Siguiente
    dia_anterior = fecha_seleccionada - timedelta(days=1)
    dia_siguiente = fecha_seleccionada + timedelta(days=1)
    if dia_anterior < date.today():
        dia_anterior = None

    # 3. LÓGICA DE TURNOS
    horarios_disponibles = []
    
    citas_ocupadas = Cita.objects.filter(
        medico=medico,
        fecha=fecha_seleccionada,
        estado='PENDIENTE'
    ).values_list('hora', flat=True)
    
    lista_horas_ocupadas = [t.strftime('%H:%M') for t in citas_ocupadas]

    if medico.hora_inicio and medico.hora_fin:
        hora_actual = medico.hora_inicio
        while hora_actual < medico.hora_fin:
            hora_actual_str = hora_actual.strftime('%H:%M')
            esta_ocupado = hora_actual_str in lista_horas_ocupadas
            
            horarios_disponibles.append({
                'hora': hora_actual,
                'ocupado': esta_ocupado 
            })
            
            dt = datetime.combine(date.today(), hora_actual) + timedelta(minutes=30)
            hora_actual = dt.time()

    # 4. Procesar Reserva (POST)
    if request.method == 'POST':
        try:
            hora_post = request.POST.get('hora')
            
            # --- AQUÍ ESTÁ LA CORRECCIÓN CLAVE ---
            if es_medico:
                # Si soy médico, obtengo el ID del paciente desde el formulario
                paciente_id = request.POST.get('paciente_id')
                if not paciente_id:
                    raise Exception("Debes seleccionar un paciente.")
                paciente = get_object_or_404(Paciente, id=paciente_id)
            else:
                # Si soy paciente, me uso a mí mismo
                paciente = request.user.perfil_paciente

            # Guardamos la cita
            Cita.objects.create(
                medico=medico,
                paciente=paciente,
                fecha=fecha_seleccionada,
                hora=hora_post,
                estado='PENDIENTE'
            )
            messages.success(request, '¡Cita reservada con éxito!')
            
            # Si es médico, quizás quieras volver a la agenda, si es paciente al home
            if es_medico:
                return redirect('ver_agenda') 
            return redirect('home')
            
        except AttributeError:
            messages.error(request, 'Error: Tu usuario no tiene perfil de paciente.')
        except Exception as e:
            messages.error(request, f'Error al reservar: {e}')

    return render(request, 'reservar_cita.html', {
        'medico': medico,
        'horarios': horarios_disponibles,
        'fecha_seleccionada': fecha_seleccionada,
        'dia_anterior': dia_anterior,
        'dia_siguiente': dia_siguiente,
        'es_medico': es_medico,          # <--- Pasamos este dato al HTML
        'lista_pacientes': lista_pacientes # <--- Pasamos la lista al HTML
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
            cita.estado = 'CANCELADA'
            cita.save()
            messages.warning(request, 'Cita cancelada.')
        elif accion == 'finalizar':
            cita.estado = 'FINALIZADA'
            cita.save()
            messages.success(request, 'Cita finalizada.')
            
        return redirect(f'/citas/agenda/?fecha={fecha_agenda}')

    return render(request, 'ver_agenda.html', {
        'citas': citas,
        'fecha_agenda': fecha_agenda,
        'hoy': date.today()
    })
