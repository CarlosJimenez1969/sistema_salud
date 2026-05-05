from datetime import datetime
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.contrib import messages
from django.db.models import Q
from xhtml2pdf import pisa
from citas.models import Cita
from paciente.models import Paciente
from .models import (
    HistoriaClinica, ImagenHistoria, HistoriaOftalmologia, HistoriaPediatria,
    HistoriaGinecologia, HistoriaCardiologia, HistoriaDermatologia, HistoriaOdontologia,
    HistoriaPsicologia, HistoriaNutricion, HistoriaOtorrino, HistoriaTraumatologia,
    Receta, HistoriaGastro, HistoriaPsiquiatria, HistoriaReumatologia, HistoriaGeriatria
)
from .forms import HistoriaForm, TriajeForm, RecetaForm
from .utils import enviar_receta_email
from users.decorators import medico_required

@login_required
@medico_required
def crear_historia(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    medico = request.user.perfil_medico
    hoy = timezone.now().date()
    
    # 1. BUSCAR TRIAJE DEL DÍA (modelo Triaje, registrado por la secretaria)
    from .models import Triaje
    triaje_previo = Triaje.objects.filter(
        paciente=paciente,
        cita__fecha=hoy
    ).order_by('-fecha_registro').first()

    # 2. DETECCIÓN DE ESPECIALIDADES (Lógica de nombres)
    esp_nombre = medico.especialidad.nombre.lower() if medico.especialidad else ""
    es_oftalmologo = "oftalm" in esp_nombre
    es_pediatra = "pediat" in esp_nombre
    es_ginecologo = "ginec" in esp_nombre or "obstet" in esp_nombre
    es_cardiologo = "cardio" in esp_nombre
    es_dermatologo = "derma" in esp_nombre
    es_odontologo = "odont" in esp_nombre or "dentis" in esp_nombre
    es_psicologo = "psico" in esp_nombre
    es_nutricionista = "nutri" in esp_nombre
    es_otorrino = "otorrino" in esp_nombre or "orl" in esp_nombre
    es_traumatologo = "trauma" in esp_nombre or "ortop" in esp_nombre
    es_gastro = "gastro" in esp_nombre
    es_psiquiatra = "psiquia" in esp_nombre
    es_reumato = "reuma" in esp_nombre
    es_geriatra = "geria" in esp_nombre
    es_neurologo = "neurolog" in esp_nombre
    es_endocrinologo = "endocrin" in esp_nombre
    es_internista = "interna" in esp_nombre or "intern" in esp_nombre
    es_cirujano = "cirug" in esp_nombre
    es_urologo = "urol" in esp_nombre
    es_neumolog = "neumo" in esp_nombre or "pulmon" in esp_nombre
    es_nefrologo = "nefro" in esp_nombre
    es_emergencias = "emergencia" in esp_nombre or "urgencia" in esp_nombre
    es_veterinario = "veterin" in esp_nombre

    # Si no hay triaje de hoy, usar signos vitales de la última consulta
    if not triaje_previo:
        ultima_historia = HistoriaClinica.objects.filter(
            paciente=paciente
        ).order_by('-fecha_atencion').first()
    else:
        ultima_historia = None

    if request.method == 'POST':
        form = HistoriaForm(request.POST)
        imagenes = request.FILES.getlist('imagenes_campo') 
        
        if form.is_valid():
            # Guardar encabezado de historia
            historia = form.save(commit=False)
            historia.paciente = paciente
            historia.medico = medico
            historia.fecha_atencion = timezone.now()
            # Si es veterinario, vincular la mascota desde la cita
            if es_veterinario:
                from citas.models import Cita
                cita_actual = Cita.objects.filter(medico=medico, paciente=paciente, mascota__isnull=False).order_by('-fecha', '-hora').first()
                if cita_actual:
                    historia.mascota = cita_actual.mascota
            historia.save()

            # 3. GUARDAR DATOS ESPECÍFICOS POR ESPECIALIDAD
            if es_oftalmologo:
                HistoriaOftalmologia.objects.create(
                    historia_clinica=historia,
                    agudeza_visual_od=request.POST.get('agudeza_od'),
                    agudeza_visual_oi=request.POST.get('agudeza_oi'),
                    presion_intraocular_od=request.POST.get('presion_od'),
                    presion_intraocular_oi=request.POST.get('presion_oi'),
                    fondo_ojo=request.POST.get('fondo_ojo')
                )
            elif es_pediatra:
                HistoriaPediatria.objects.create(
                    historia_clinica=historia,
                    tipo_parto=request.POST.get('tipo_parto'),
                    apgar=request.POST.get('apgar'),
                    peso_nacimiento=request.POST.get('peso_nacimiento'),
                    lactancia=request.POST.get('lactancia'),
                    vacunas_completas=request.POST.get('vacunas') == 'on',
                    observaciones_crecimiento=request.POST.get('observaciones_crecimiento')
                )
            elif es_ginecologo:
                fecha_fum = request.POST.get('fum') or None
                HistoriaGinecologia.objects.create(
                    historia_clinica=historia, fum=fecha_fum,
                    ciclo_menstrual=request.POST.get('ciclo_menstrual'),
                    gestas=request.POST.get('gestas') or 0,
                    partos=request.POST.get('partos') or 0,
                    cesareas=request.POST.get('cesareas') or 0,
                    abortos=request.POST.get('abortos') or 0,
                    anticonceptivos=request.POST.get('anticonceptivos')
                )
            elif es_cardiologo:
                 HistoriaCardiologia.objects.create(
                    historia_clinica=historia,
                    riesgo=request.POST.get('riesgo'),
                    antecedentes_familiares=request.POST.get('antecedentes_familiares'),
                    electrocardiograma=request.POST.get('electrocardiograma'),
                    ecocardiograma=request.POST.get('ecocardiograma'),
                    clase_funcional=request.POST.get('clase_funcional')
                )
            elif es_dermatologo:
                biopsia_val = request.POST.get('biopsia') == 'on'
                HistoriaDermatologia.objects.create(
                    historia_clinica=historia,
                    fototipo=request.POST.get('fototipo'),
                    lesion_primaria=request.POST.get('lesion_primaria'),
                    localizacion=request.POST.get('localizacion'),
                    distribucion=request.POST.get('distribucion'),
                    biopsia=biopsia_val
                )
            elif es_odontologo:
                fecha_cita = request.POST.get('proxima_cita')
                if not fecha_cita: fecha_cita = None
                HistoriaOdontologia.objects.create(
                    historia_clinica=historia,
                    higiene_oral=request.POST.get('higiene_oral'),
                    encias=request.POST.get('encias'),
                    dientes_tratados=request.POST.get('dientes_tratados'),
                    procedimiento=request.POST.get('procedimiento'),
                    proxima_cita=fecha_cita
                )
            elif es_psicologo:
                HistoriaPsicologia.objects.create(
                    historia_clinica=historia,
                    apariencia_comportamiento=request.POST.get('apariencia_comportamiento'),
                    estado_animo=request.POST.get('estado_animo'),
                    funciones_cognitivas=request.POST.get('funciones_cognitivas'),
                    sueno_apetito=request.POST.get('sueno_apetito'),
                    plan_sesiones=request.POST.get('plan_sesiones')
                )
            elif es_nutricionista:
                HistoriaNutricion.objects.create(
                    historia_clinica=historia,
                    imc=request.POST.get('imc'),
                    grasa_corporal=request.POST.get('grasa_corporal'),
                    masa_muscular=request.POST.get('masa_muscular'),
                    circunferencia_cintura=request.POST.get('circunferencia_cintura'),
                    circunferencia_cadera=request.POST.get('circunferencia_cadera'),
                    tipo_dieta=request.POST.get('tipo_dieta')
                )
            elif es_otorrino:
                HistoriaOtorrino.objects.create(
                    historia_clinica=historia,
                    otoscopia_od=request.POST.get('otoscopia_od'),
                    otoscopia_oi=request.POST.get('otoscopia_oi'),
                    rinoscopia=request.POST.get('rinoscopia'),
                    tabique=request.POST.get('tabique'),
                    orofaringe=request.POST.get('orofaringe'),
                    audiometria=request.POST.get('audiometria')
                )
            elif es_traumatologo:
                HistoriaTraumatologia.objects.create(
                    historia_clinica=historia,
                    zona_afectada=request.POST.get('zona_afectada'),
                    mecanismo_lesion=request.POST.get('mecanismo_lesion'),
                    movilidad=request.POST.get('movilidad'),
                    fuerza_muscular=request.POST.get('fuerza_muscular'),
                    sensibilidad=request.POST.get('sensibilidad'),
                    pruebas_especiales=request.POST.get('pruebas_especiales'),
                    plan_rehabilitacion=request.POST.get('plan_rehabilitacion')
                )
            elif es_gastro:
                HistoriaGastro.objects.create(
                    historia_clinica=historia,
                    dolor_abdominal=request.POST.get('dolor_abdominal'),
                    habito_intestinal=request.POST.get('habito_intestinal'),
                    endoscopia_previa=request.POST.get('endoscopia_previa')
                )
            elif es_psiquiatra:
                HistoriaPsiquiatria.objects.create(
                    historia_clinica=historia,
                    examen_mental=request.POST.get('examen_mental'),
                    ideacion_suicida=request.POST.get('ideacion_suicida') == 'on',
                    medicacion_psicotropica=request.POST.get('medicacion')
                )
            elif es_reumato:
                HistoriaReumatologia.objects.create(
                    historia_clinica=historia,
                    rigidez_matutina=request.POST.get('rigidez'),
                    articulaciones_afectadas=request.POST.get('articulaciones'),
                    factor_reumatoide=request.POST.get('factor_reumatoide')
                )
            elif es_geriatra:
                HistoriaGeriatria.objects.create(
                    historia_clinica=historia,
                    escala_kartz=request.POST.get('escala_kartz'),
                    deterioro_cognitivo=request.POST.get('deterioro_cognitivo'),
                    polifarmacia=request.POST.get('polifarmacia')
                )
            elif es_neurologo:
                from .models import HistoriaNeurologia
                HistoriaNeurologia.objects.create(
                    historia_clinica=historia,
                    escala_glasgow=request.POST.get('glasgow'),
                    pares_craneales=request.POST.get('pares_craneales'),
                    fuerza_motora=request.POST.get('fuerza_motora'),
                    reflejos=request.POST.get('reflejos'),
                    coordinacion=request.POST.get('coordinacion'),
                    sensibilidad_neuro=request.POST.get('sensibilidad_neuro'),
                    neuroimagen=request.POST.get('neuroimagen'),
                    escala_nihss=request.POST.get('nihss'),
                )
            elif es_endocrinologo:
                from .models import HistoriaEndocrinologia
                HistoriaEndocrinologia.objects.create(
                    historia_clinica=historia,
                    tipo_diabetes=request.POST.get('tipo_diabetes', 'OTRO'),
                    glucosa_ayunas=request.POST.get('glucosa_ayunas'),
                    hba1c=request.POST.get('hba1c'),
                    insulina_basal=request.POST.get('insulina_basal'),
                    tsh=request.POST.get('tsh'),
                    t3_t4=request.POST.get('t3_t4'),
                    cortisol=request.POST.get('cortisol'),
                    objetivos_terapeuticos=request.POST.get('objetivos_terapeuticos'),
                )
            elif es_internista:
                from .models import HistoriaMedicinaInterna
                HistoriaMedicinaInterna.objects.create(
                    historia_clinica=historia,
                    mucosas=request.POST.get('mucosas'),
                    ganglios=request.POST.get('ganglios'),
                    tiroides_examen=request.POST.get('tiroides_examen'),
                    examen_pulmonar=request.POST.get('examen_pulmonar'),
                    examen_cardiaco=request.POST.get('examen_cardiaco'),
                    examen_abdominal=request.POST.get('examen_abdominal'),
                    examen_extremidades=request.POST.get('examen_extremidades'),
                    examenes_laboratorio=request.POST.get('examenes_laboratorio'),
                )
            elif es_cirujano:
                from .models import HistoriaCirugia
                fecha_cx = request.POST.get('fecha_cirugia') or None
                HistoriaCirugia.objects.create(
                    historia_clinica=historia,
                    tipo_cirugia=request.POST.get('tipo_cirugia'),
                    clasificacion_asa=request.POST.get('clasificacion_asa', 'I'),
                    hallazgos_intraop=request.POST.get('hallazgos_intraop'),
                    tecnica_quirurgica=request.POST.get('tecnica_quirurgica'),
                    complicaciones_qx=request.POST.get('complicaciones_qx'),
                    plan_postoperatorio=request.POST.get('plan_postoperatorio'),
                    fecha_cirugia=fecha_cx,
                )
            elif es_urologo:
                from .models import HistoriaUrologia
                HistoriaUrologia.objects.create(
                    historia_clinica=historia,
                    sintomas_miccionales=request.POST.get('sintomas_miccionales'),
                    psa=request.POST.get('psa'),
                    creatinina_uro=request.POST.get('creatinina_uro'),
                    urocultivo=request.POST.get('urocultivo'),
                    ecografia=request.POST.get('ecografia_uro'),
                    residuo_postmiccional=request.POST.get('residuo_postmiccional'),
                    cistoscopia=request.POST.get('cistoscopia'),
                )
            elif es_neumolog:
                from .models import HistoriaNeurologia_Neumologia
                HistoriaNeurologia_Neumologia.objects.create(
                    historia_clinica=historia,
                    saturacion_o2=request.POST.get('saturacion_o2'),
                    fev1=request.POST.get('fev1'),
                    fvc=request.POST.get('fvc'),
                    relacion_fev1_fvc=request.POST.get('fev1_fvc'),
                    patron_espirometrico=request.POST.get('patron_espirometrico', 'NORMAL'),
                    tabaquismo=request.POST.get('tabaquismo', 'NO'),
                    indice_paquete_anio=request.POST.get('indice_paquete'),
                    rx_tac_torax=request.POST.get('rx_tac_torax'),
                )
            elif es_nefrologo:
                from .models import HistoriaNefrologia
                HistoriaNefrologia.objects.create(
                    historia_clinica=historia,
                    creatinina_nef=request.POST.get('creatinina_nef'),
                    tfg=request.POST.get('tfg'),
                    proteinuria=request.POST.get('proteinuria'),
                    urea_bun=request.POST.get('urea_bun'),
                    estadio_erc=request.POST.get('estadio_erc', '1'),
                    en_hemodialisis=request.POST.get('hemodialisis') == 'on',
                    acceso_vascular=request.POST.get('acceso_vascular'),
                    control_pa=request.POST.get('control_pa_nef'),
                )
            elif es_emergencias:
                from .models import HistoriaEmergencias
                HistoriaEmergencias.objects.create(
                    historia_clinica=historia,
                    nivel_triage=request.POST.get('nivel_triage', '3'),
                    mecanismo_trauma=request.POST.get('mecanismo_trauma'),
                    glasgow_emergencia=request.POST.get('glasgow_emergencia'),
                    via_aerea=request.POST.get('via_aerea'),
                    respiracion_emerg=request.POST.get('respiracion_emerg'),
                    circulacion_emerg=request.POST.get('circulacion_emerg'),
                    procedimientos=request.POST.get('procedimientos_emerg'),
                    medicacion_urgente=request.POST.get('medicacion_urgente'),
                    destino_paciente=request.POST.get('destino_paciente', 'ALTA'),
                )
            elif es_veterinario:
                from .models import HistoriaVeterinaria
                HistoriaVeterinaria.objects.create(
                    historia_clinica=historia,
                    temperatura=request.POST.get('vet_temperatura') or None,
                    frecuencia_card=request.POST.get('vet_fc') or None,
                    frecuencia_resp=request.POST.get('vet_fr') or None,
                    peso_actual=request.POST.get('vet_peso') or None,
                    condicion_corporal=request.POST.get('vet_condicion', ''),
                    vacunas_aplicadas=request.POST.get('vet_vacunas', ''),
                    proxima_vacuna=request.POST.get('vet_proxima_vacuna') or None,
                    desparasitacion=request.POST.get('vet_desparasitacion', ''),
                    proxima_desparasitacion=request.POST.get('vet_proxima_desp') or None,
                    mucosas=request.POST.get('vet_mucosas', ''),
                    hidratacion=request.POST.get('vet_hidratacion', ''),
                    observaciones_examen=request.POST.get('vet_observaciones', ''),
                )

            # 4. GUARDAR IMÁGENES
            for imagen_file in imagenes:
                ImagenHistoria.objects.create(historia=historia, archivo=imagen_file)

           # 5. ACTUALIZAR ESTADO DE CITA ACTUAL A FINALIZADA ('A')
            cita_actual = Cita.objects.filter(
                paciente=paciente, medico=medico, fecha=hoy
            ).filter(Q(estado='P') | Q(estado='E')).first()

            if cita_actual:
                cita_actual.estado = 'A' 
                cita_actual.save(update_fields=['estado'])

           # --- 6. LÓGICA CRÍTICA: CREAR LA CITA DE CONTROL FÍSICA ---
            fecha_hora_raw = request.POST.get('proxima_cita_control')
            msg_control = ""

            if fecha_hora_raw:
                try:
                    # Limpiamos el formato (algunos navegadores ponen una 'T')
                    dt_str = fecha_hora_raw.replace('T', ' ')
                    dt_obj = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
                    descripcion_motivo = getattr(historia, 'motivo_consulta', 'Cita de Control')
                    
                    # CREAMOS LA CITA EN LA TABLA DE CITAS
                    Cita.objects.create(
                        paciente=paciente,
                        medico=medico,
                        fecha=dt_obj.date(),
                        hora=dt_obj.time(),
                        motivo=f"CONTROL: {descripcion_motivo[:50]}",
                        estado='P'  # Se guarda como Pendiente para que aparezca en la agenda
                    )
                    print(f"Cita creada para el {dt_obj}")
                    msg_control = f" Control agendado para el {dt_obj.strftime('%d/%m/%Y %H:%M')}."
                except Exception as e:
                    # Esto te ayudará a ver en la terminal si algo falla
                    print(f"Error al crear la cita de control: {e}")

            # --- 7. SIGUIENTE PACIENTE, ENVÍO DE CORREO Y REDIRECCIÓN ---
            
            # Buscamos quién sigue en la agenda
            siguiente_cita = Cita.objects.filter(
                medico=medico, fecha=hoy,
                estado__in=['P', 'E']
            ).exclude(paciente=paciente).order_by('hora').first()

            msg_next = f" Siguiente: {siguiente_cita.paciente.usuario.get_full_name()}." if siguiente_cita else ""

            # Intentamos enviar el correo con la receta PDF
            try:
                exito_mail, mensaje_mail = enviar_receta_email(historia)
                if exito_mail:
                    msg_final = f"Consulta guardada.{msg_control}{msg_next} 📧 Receta enviada al correo."
                else:
                    # Caso donde no hay correo o el servidor SMTP falló con un mensaje controlado
                    msg_final = f"Consulta guardada.{msg_control}{msg_next} ⚠️ Nota: {mensaje_mail}"
            except Exception as e:
                # Caso de error técnico inesperado
                print(f"Error crítico en envío de correo: {e}")
                msg_final = f"Consulta guardada.{msg_control}{msg_next} (El envío automático falló)."

            # Mostramos el mensaje final unificado al médico
            messages.success(request, msg_final)
            
            return redirect('historial_medico', paciente_id=paciente.id)
    else:
        initial = {}
        if triaje_previo:
            initial = {
                'temperatura':      triaje_previo.temperatura,
                'presion_arterial': triaje_previo.presion_arterial,
                'pulso':            triaje_previo.frecuencia_cardiaca,
                'peso':             triaje_previo.peso,
                'altura':           triaje_previo.talla,
            }
        elif ultima_historia:
            initial = {
                'temperatura':      ultima_historia.temperatura,
                'presion_arterial': ultima_historia.presion_arterial,
                'pulso':            ultima_historia.pulso,
                'peso':             ultima_historia.peso,
                'altura':           ultima_historia.altura,
            }
        form = HistoriaForm(initial=initial)

    return render(request, 'historia/crear_historia.html', {
        'form': form, 
        'paciente': paciente,
        'triaje_cargado': bool(triaje_previo),
        'vitales_ultima_consulta': bool(ultima_historia and not triaje_previo),
        'es_oftalmologo': es_oftalmologo, 'es_pediatra': es_pediatra,
        'es_ginecologo': es_ginecologo, 'es_cardiologo': es_cardiologo,
        'es_dermatologo': es_dermatologo, 'es_odontologo': es_odontologo,
        'es_psicologo': es_psicologo, 'es_nutricionista': es_nutricionista,
        'es_otorrino': es_otorrino, 'es_traumatologo': es_traumatologo,
        'es_gastro': es_gastro, 'es_psiquiatra': es_psiquiatra,
        'es_reumato': es_reumato, 'es_geriatra': es_geriatra,
        'es_neurologo': es_neurologo, 'es_endocrinologo': es_endocrinologo,
        'es_internista': es_internista, 'es_cirujano': es_cirujano,
        'es_urologo': es_urologo, 'es_neumolog': es_neumolog,
        'es_nefrologo': es_nefrologo, 'es_emergencias': es_emergencias,
        'es_veterinario': es_veterinario,
    })

# Vista extra para VER una historia pasada (Lectura)
@login_required
@medico_required
def ver_historia(request, historia_id):
    historia = get_object_or_404(HistoriaClinica, id=historia_id)
    return render(request, 'ver_historia.html', {'h': historia})

#Esta función busca todas las historias del paciente
@login_required
def historial_medico(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    role = getattr(request.user, 'role', '')

    # ADMIN ve todo; MEDICO/SECRETARIA solo si tienen relación con el paciente; PACIENTE solo lo suyo
    from citas.models import Cita
    if role == 'ADMIN':
        pass
    elif role == 'MEDICO' and hasattr(request.user, 'perfil_medico'):
        if not Cita.objects.filter(medico=request.user.perfil_medico, paciente=paciente).exists():
            messages.error(request, "No tiene permiso para ver este historial.")
            return redirect('home')
    elif role == 'SECRETARIA' and hasattr(request.user, 'perfil_secretaria'):
        medico = request.user.perfil_secretaria.medico
        if not Cita.objects.filter(medico=medico, paciente=paciente).exists():
            messages.error(request, "No tiene permiso para ver este historial.")
            return redirect('dashboard_secretaria')
    elif role == 'PACIENTE' and hasattr(request.user, 'perfil_paciente'):
        if request.user.perfil_paciente.id != paciente.id:
            messages.error(request, "No tiene permiso para ver este historial.")
            return redirect('home')
    else:
        messages.error(request, "Acceso denegado.")
        return redirect('home')

    historias = HistoriaClinica.objects.filter(paciente=paciente).order_by('-fecha_atencion')

    return render(request, 'historial_medico.html', {
        'paciente': paciente,
        'historias': historias
    })

@login_required
def imprimir_receta(request, historia_id):
    historia = get_object_or_404(HistoriaClinica, id=historia_id)

    # Si ya existe el PDF guardado en Cloudinary, lo redirigimos directamente
    if historia.receta_pdf:
        return redirect(historia.receta_pdf.url)

    # Generar PDF la primera vez
    from io import BytesIO
    from django.core.files.base import ContentFile
    template = get_template('historia/receta_pdf.html')
    html = template.render({'h': historia})
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF <pre>' + html + '</pre>')

    # Guardar el PDF en Cloudinary
    pdf_bytes = buffer.getvalue()
    filename = f"receta_{historia.id}.pdf"
    historia.receta_pdf.save(filename, ContentFile(pdf_bytes), save=True)

    # Devolver el PDF al navegador
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@login_required
@medico_required # Solo el médico receta
def crear_receta(request, historia_id):
    historia = get_object_or_404(HistoriaClinica, id=historia_id)
    
    # Verificamos si ya tiene receta para no duplicar
    if hasattr(historia, 'receta'):
        return redirect('editar_receta', receta_id=historia.receta.id)

    if request.method == 'POST':
        form = RecetaForm(request.POST)
        if form.is_valid():
            receta = form.save(commit=False)
            receta.historia_clinica = historia
            receta.save()
            messages.success(request, "Receta generada con éxito.")
            # Luego cambiaremos esto para que redirija al PDF
            return redirect('dashboard_secretaria')
    else:
        form = RecetaForm()

    return render(request, 'historia/crear_receta.html', {
        'form': form, 
        'historia': historia
    })

def obtener_ultimos_signos(request, paciente_id):
    # Buscamos la historia más reciente de este paciente
    ultima_historia = HistoriaClinica.objects.filter(paciente_id=paciente_id).order_by('-fecha_atencion').first()
    
    if ultima_historia:
        data = {
            'temperatura': str(ultima_historia.temperatura),
            'presion_arterial': ultima_historia.presion_arterial,
            'pulso': ultima_historia.pulso,
            'peso': str(ultima_historia.peso),
            'altura': str(ultima_historia.altura),
        }
        return JsonResponse(data)
    return JsonResponse({'error': 'No hay registros previos'}, status=404)

@login_required
def registrar_triaje(request, cita_id):
    from .models import Triaje
    role = getattr(request.user, 'role', '')
    if role not in ('ADMIN', 'MEDICO', 'SECRETARIA'):
        messages.error(request, "Acceso denegado.")
        return redirect('home')

    if role == 'SECRETARIA' and hasattr(request.user, 'perfil_secretaria'):
        cita = get_object_or_404(Cita, id=cita_id, medico=request.user.perfil_secretaria.medico)
    elif role == 'MEDICO' and hasattr(request.user, 'perfil_medico'):
        cita = get_object_or_404(Cita, id=cita_id, medico=request.user.perfil_medico)
    else:
        cita = get_object_or_404(Cita, id=cita_id)
    paciente = cita.paciente

    # Buscar triaje existente para esta cita (si ya fue registrado)
    triaje_existente = Triaje.objects.filter(cita=cita).first()

    if request.method == 'POST':
        form = TriajeForm(request.POST, instance=triaje_existente)
        if form.is_valid():
            triaje = form.save(commit=False)
            triaje.paciente = paciente
            triaje.cita = cita
            triaje.save()

            cita.estado = 'E'
            cita.save()

            messages.success(request, f"Triaje de {paciente.usuario.get_full_name()} guardado.")
            # Redirigir según el rol: secretaria va a su dashboard, médico va a su agenda
            if request.user.role == 'SECRETARIA':
                return redirect('dashboard_secretaria')
            return redirect('ver_agenda')
    else:
        form = TriajeForm(instance=triaje_existente)

    return render(request, 'historia/triaje.html', {
        'form': form,
        'paciente': paciente, 
        'cita': cita
    })