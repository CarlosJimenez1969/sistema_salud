from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from paciente.models import Paciente
from .models import HistoriaClinica, ImagenHistoria, HistoriaOftalmologia, HistoriaPediatria, HistoriaGinecologia, HistoriaCardiologia, HistoriaDermatologia, HistoriaOdontologia, HistoriaPsicologia, HistoriaNutricion, HistoriaOtorrino, HistoriaTraumatologia
from .forms import HistoriaForm
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

@login_required
def crear_historia(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    medico = request.user.perfil_medico
    
    # 1. DETECCIÓN DE ESPECIALIDAD
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

    if request.method == 'POST':
        form = HistoriaForm(request.POST)
        imagenes = request.FILES.getlist('imagenes_campo') 
        
        if form.is_valid():
            # Guardar Historia Padre
            historia = form.save(commit=False)
            historia.paciente = paciente
            historia.medico = medico
            historia.save()
            
            # --- GUARDAR DATOS ESPECÍFICOS ---
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
                vacunas = request.POST.get('vacunas') == 'on'
                HistoriaPediatria.objects.create(
                    historia_clinica=historia,
                    tipo_parto=request.POST.get('tipo_parto'),
                    apgar=request.POST.get('apgar'),
                    peso_nacimiento=request.POST.get('peso_nacimiento'),
                    lactancia=request.POST.get('lactancia'),
                    vacunas_completas=vacunas,
                    observaciones_crecimiento=request.POST.get('observaciones_crecimiento')
                )
            elif es_ginecologo:
                fecha_fum = request.POST.get('fum')
                if not fecha_fum: fecha_fum = None 
                HistoriaGinecologia.objects.create(
                    historia_clinica=historia,
                    fum=fecha_fum,
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
            
            for imagen_file in imagenes:
                ImagenHistoria.objects.create(historia=historia, archivo=imagen_file)
            
            return redirect('historial_medico', paciente_id=paciente.id)        
        else:
            print(form.errors)
    else:
        form = HistoriaForm()

    return render(request, 'crear_historia.html', {
        'form': form, 
        'paciente': paciente,
        'es_oftalmologo': es_oftalmologo,
        'es_pediatra': es_pediatra,
        'es_ginecologo': es_ginecologo,
        'es_cardiologo': es_cardiologo,
        'es_dermatologo': es_dermatologo,
        'es_odontologo': es_odontologo,
        'es_psicologo': es_psicologo,
        'es_nutricionista': es_nutricionista,
        'es_otorrino': es_otorrino,
        'es_traumatologo': es_traumatologo  # <--- PASAR AL HTML
    })

# Vista extra para VER una historia pasada (Lectura)
@login_required
def ver_historia(request, historia_id):
    historia = get_object_or_404(HistoriaClinica, id=historia_id)
    return render(request, 'ver_historia.html', {'h': historia})

#Esta función busca todas las historias del paciente
@login_required
def historial_medico(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    # Traemos todas las historias de este paciente, ordenadas de la más reciente a la más antigua
    historias = HistoriaClinica.objects.filter(paciente=paciente).order_by('-fecha_atencion')
    
    return render(request, 'historial_medico.html', {
        'paciente': paciente,
        'historias': historias
    })

@login_required
def imprimir_receta(request, historia_id):
    # 1. Buscamos la historia clínica específica
    historia = get_object_or_404(HistoriaClinica, id=historia_id)
    
    # 2. Definimos qué plantilla HTML usaremos para el diseño
    template_path = 'receta_pdf.html'
    context = {'h': historia} # Pasamos los datos
    
    # 3. Preparamos la respuesta (tipo PDF)
    response = HttpResponse(content_type='application/pdf')
    # Si quieres que se descargue directo, usa 'attachment'. Si quieres verla en el navegador, usa 'inline'
    response['Content-Disposition'] = f'inline; filename="receta_{historia.id}.pdf"'

    # 4. Renderizamos (Magia: HTML -> PDF)
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(
       html, dest=response
    )
    
    # 5. Si hay error, mostramos el HTML feo para depurar
    if pisa_status.err:
       return HttpResponse('Error al generar PDF <pre>' + html + '</pre>')
    
    return response