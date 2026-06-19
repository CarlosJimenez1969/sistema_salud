from django.db import models
from paciente.models import Paciente
from medico.models import Medico

class HistoriaClinica(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='historias')
    medico = models.ForeignKey(Medico, on_delete=models.PROTECT, related_name='historias_creadas')
    fecha_atencion = models.DateTimeField(auto_now_add=True)
    
    # --- SECCIÓN 1: MOTIVO Y ENFERMEDAD (MSP Formulario 002) ---
    motivo_consulta = models.TextField(help_text="Motivo por el cual viene el paciente")
    enfermedad_actual = models.TextField(help_text="Descripción detallada de la molestia")

    # --- SECCIÓN 1b: ANTECEDENTES (MSP Formulario 002 - obligatorio) ---
    antecedentes_personales = models.TextField(
        blank=True, null=True,
        verbose_name="Antecedentes Personales",
        help_text="Enfermedades previas, cirugías, alergias, medicamentos actuales"
    )
    antecedentes_familiares = models.TextField(
        blank=True, null=True,
        verbose_name="Antecedentes Familiares",
        help_text="Enfermedades hereditarias o relevantes en familiares directos"
    )
    revision_sistemas = models.TextField(
        blank=True, null=True,
        verbose_name="Revisión de Órganos y Sistemas",
        help_text="Síntomas positivos y negativos relevantes por sistemas"
    )

    # --- SECCIÓN 2: SIGNOS VITALES ---
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, help_text="°C", null=True, blank=True)
    presion_arterial = models.CharField(max_length=20, help_text="Ej: 120/80", null=True, blank=True)
    pulso = models.IntegerField(help_text="Latidos por minuto", null=True, blank=True)
    peso = models.DecimalField(max_digits=5, decimal_places=2, help_text="Kg", null=True, blank=True)
    altura = models.DecimalField(max_digits=5, decimal_places=2, help_text="Metros o CM", null=True, blank=True)
    
    # --- SECCIÓN 3: EXAMEN Y DIAGNÓSTICO (MSP Formulario 002) ---
    examen_fisico = models.TextField(help_text="Hallazgos del examen físico")
    TIPO_DX = [('PRESUNTIVO', 'Presuntivo'), ('DEFINITIVO', 'Definitivo')]
    tipo_diagnostico = models.CharField(
        max_length=12, choices=TIPO_DX, default='PRESUNTIVO',
        verbose_name="Tipo de Diagnóstico"
    )
    diagnostico = models.TextField(help_text="Diagnóstico CIE-10")
    tratamiento = models.TextField(help_text="Indicaciones y medicamentos")
    plan_educacional = models.TextField(
        blank=True, null=True,
        verbose_name="Plan Educacional",
        help_text="Instrucciones y educación entregada al paciente"
    )

    proxima_cita_control = models.DateTimeField(null=True, blank=True)
    signos_alarma = models.TextField(
        null=True,
        blank=True,
        #help_text="Instrucciones de emergencia para el paciente"
        default=""
    )

    # PDF de la receta generado y guardado en Cloudinary la primera vez que se imprime
    receta_pdf = models.FileField(upload_to='recetas/', null=True, blank=True)

    # Solo para citas veterinarias: el paciente es el dueño y la mascota es el "paciente real"
    mascota = models.ForeignKey('paciente.Mascota', on_delete=models.PROTECT, null=True, blank=True, related_name='historias')

    def __str__(self):
        return f"Historia {self.id} - {self.paciente} ({self.fecha_atencion.date()})"


class HistoriaVeterinaria(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='veterinaria')

    # Signos vitales animales
    temperatura      = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="°C")
    frecuencia_card  = models.IntegerField(null=True, blank=True, verbose_name="Frecuencia cardiaca (lpm)")
    frecuencia_resp  = models.IntegerField(null=True, blank=True, verbose_name="Frecuencia respiratoria (rpm)")
    peso_actual      = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Kg")
    condicion_corporal = models.CharField(max_length=20, blank=True, choices=[
        ('1', '1 - Caquexia'),
        ('2', '2 - Bajo peso'),
        ('3', '3 - Ideal'),
        ('4', '4 - Sobrepeso'),
        ('5', '5 - Obesidad'),
    ])

    # Vacunación y desparasitación
    vacunas_aplicadas        = models.TextField(blank=True, verbose_name="Vacunas aplicadas hoy")
    proxima_vacuna           = models.DateField(null=True, blank=True)
    desparasitacion          = models.TextField(blank=True, verbose_name="Desparasitación aplicada")
    proxima_desparasitacion  = models.DateField(null=True, blank=True)

    # Examen clínico
    mucosas        = models.CharField(max_length=50, blank=True, choices=[
        ('NORMAL',     'Rosadas (Normal)'),
        ('PALIDAS',    'Pálidas'),
        ('CIANOTICAS', 'Cianóticas'),
        ('ICTERICAS',  'Ictéricas'),
    ])
    hidratacion    = models.CharField(max_length=30, blank=True, choices=[
        ('NORMAL',  'Normal'),
        ('LEVE',    'Deshidratación leve (5%)'),
        ('MODERADA','Moderada (8%)'),
        ('SEVERA',  'Severa (>10%)'),
    ])
    observaciones_examen = models.TextField(blank=True, verbose_name="Observaciones del examen físico")

    def __str__(self):
        return f"Veterinaria - {self.historia_clinica.mascota or self.historia_clinica.paciente}"

# Modelo para adjuntar múltiples imágenes a una historia
class ImagenHistoria(models.Model):
    historia = models.ForeignKey(HistoriaClinica, on_delete=models.CASCADE, related_name='imagenes')
    archivo = models.ImageField(upload_to='historias_clinicas/')
    descripcion = models.CharField(max_length=200, blank=True)
    subido_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Imagen para historia {self.historia.id}"
    
class HistoriaOftalmologia(models.Model):
    # Relación 1 a 1: Una historia clínica tiene UN detalle oftalmológico
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='oftalmologia')
    
    # Datos específicos de la especialidad
    agudeza_visual_od = models.CharField(max_length=50, verbose_name="Agudeza Visual Ojo Der.", default="20/20")
    agudeza_visual_oi = models.CharField(max_length=50, verbose_name="Agudeza Visual Ojo Izq.", default="20/20")
    presion_intraocular_od = models.CharField(max_length=50, verbose_name="Presión Ojo Der.", blank=True)
    presion_intraocular_oi = models.CharField(max_length=50, verbose_name="Presión Ojo Izq.", blank=True)
    fondo_ojo = models.TextField(verbose_name="Examen de Fondo de Ojo", blank=True)

    def __str__(self):
        return f"Oftalmología - {self.historia_clinica.paciente}"
    
class HistoriaPediatria(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='pediatria')
    
    tipo_parto = models.CharField(max_length=50, choices=[('NORMAL', 'Normal'), ('CESAREA', 'Cesárea')], verbose_name="Tipo de Parto")
    apgar = models.CharField(max_length=10, verbose_name="Test APGAR", blank=True)
    peso_nacimiento = models.CharField(max_length=20, verbose_name="Peso al Nacer", blank=True)
    lactancia = models.CharField(max_length=50, choices=[('MATERNA', 'Materna Exclusiva'), ('FORMULA', 'Fórmula'), ('MIXTA', 'Mixta')], default='MATERNA')
    vacunas_completas = models.BooleanField(default=False, verbose_name="Vacunas al día")
    observaciones_crecimiento = models.TextField(blank=True, verbose_name="Desarrollo Psicomotriz")
    
    # --- NUEVO CAMPO AGREGADO ---
    archivo_pediatrico = models.FileField(upload_to='historias/pediatria/', null=True, blank=True, verbose_name="Adjuntar Carnet/Examen")

    def __str__(self):
        return f"Pediatría - {self.historia_clinica.paciente}"

class HistoriaGinecologia(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='ginecologia')
    
    fum = models.DateField(null=True, blank=True, verbose_name="Fecha Última Menstruación (FUM)")
    ciclo_menstrual = models.CharField(max_length=50, verbose_name="Regularidad del Ciclo", blank=True)
    gestas = models.IntegerField(default=0, verbose_name="Embarazos (Gestas)")
    partos = models.IntegerField(default=0, verbose_name="Partos")
    cesareas = models.IntegerField(default=0, verbose_name="Cesáreas")
    abortos = models.IntegerField(default=0, verbose_name="Abortos")
    anticonceptivos = models.CharField(max_length=100, blank=True, verbose_name="Método Anticonceptivo")

    def __str__(self):
        return f"Gineco - {self.historia_clinica.paciente}"
    
class HistoriaCardiologia(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='cardiologia')
    
    riesgo = models.CharField(max_length=20, choices=[('BAJO', 'Bajo'), ('MODERADO', 'Moderado'), ('ALTO', 'Alto'), ('MUY_ALTO', 'Muy Alto')], verbose_name="Riesgo CV")
    antecedentes_familiares = models.TextField(blank=True, verbose_name="Antecedentes Familiares Cardíacos")
    electrocardiograma = models.TextField(blank=True, verbose_name="Resumen EKG")
    ecocardiograma = models.TextField(blank=True, verbose_name="Resumen Ecocardiograma")
    clase_funcional = models.CharField(max_length=50, choices=[('I', 'I (Sin limitaciones)'), ('II', 'II (Leve limitación)'), ('III', 'III (Marcada limitación)'), ('IV', 'IV (Incapacidad total)')], default='I')

    def __str__(self):
        return f"Cardio - {self.historia_clinica.paciente}"

class HistoriaDermatologia(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='dermatologia')
    
    fototipo = models.CharField(max_length=50, verbose_name="Fototipo de Piel (Fitzpatrick)")
    lesion_primaria = models.CharField(max_length=100, verbose_name="Lesión Primaria (Mácula, Pápula...)")
    localizacion = models.CharField(max_length=100, verbose_name="Localización")
    distribucion = models.CharField(max_length=100, verbose_name="Distribución (Simétrica, Localizada...)")
    biopsia = models.BooleanField(default=False, verbose_name="¿Requiere Biopsia?")

    def __str__(self):
        return f"Derma - {self.historia_clinica.paciente}"
    
class HistoriaOdontologia(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='odontologia')
    
    # Evaluación General
    higiene_oral = models.CharField(max_length=20, choices=[('BUENA', 'Buena'), ('REGULAR', 'Regular'), ('MALA', 'Mala')], default='REGULAR', verbose_name="Higiene Oral")
    encias = models.CharField(max_length=50, choices=[('SANAS', 'Sanas'), ('INFLAMADAS', 'Inflamadas (Gingivitis)'), ('SANGRANTES', 'Sangrantes')], default='SANAS')
    
    # Tratamiento Específico
    dientes_tratados = models.CharField(max_length=100, verbose_name="Dientes / Piezas (Ej: 18, 24, 36)", blank=True)
    procedimiento = models.TextField(verbose_name="Procedimiento Realizado (Obturación, Exodoncia, Profilaxis...)")
    
    # Plan
    proxima_cita_control = models.DateField(null=True, blank=True, verbose_name="Próxima Cita / Control")

    def __str__(self):
        return f"Odonto - {self.historia_clinica.paciente}"
    
class HistoriaPsicologia(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='psicologia')
    
    apariencia_comportamiento = models.TextField(verbose_name="Apariencia y Comportamiento")
    estado_animo = models.CharField(max_length=100, verbose_name="Estado de Ánimo / Afecto")
    funciones_cognitivas = models.TextField(verbose_name="Atención, Memoria, Lenguaje", blank=True)
    sueno_apetito = models.CharField(max_length=100, verbose_name="Sueño y Apetito", blank=True)
    plan_sesiones = models.TextField(verbose_name="Plan Terapéutico / Frecuencia")

    def __str__(self):
        return f"Psico - {self.historia_clinica.paciente}"

class HistoriaNutricion(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='nutricion')
    
    imc = models.CharField(max_length=10, verbose_name="IMC Calculado", blank=True)
    grasa_corporal = models.CharField(max_length=20, verbose_name="% Grasa Corporal", blank=True)
    masa_muscular = models.CharField(max_length=20, verbose_name="% Masa Muscular", blank=True)
    circunferencia_cintura = models.CharField(max_length=20, verbose_name="Cintura (cm)", blank=True)
    circunferencia_cadera = models.CharField(max_length=20, verbose_name="Cadera (cm)", blank=True)
    tipo_dieta = models.TextField(verbose_name="Plan Alimenticio / Tipo de Dieta")

    def __str__(self):
        return f"Nutri - {self.historia_clinica.paciente}"
    
class HistoriaOtorrino(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='otorrino')
    
    # Oídos (Otoscopia)
    otoscopia_od = models.CharField(max_length=100, verbose_name="Oído Derecho", default="Conducto permeable, Membrana timpánica íntegra")
    otoscopia_oi = models.CharField(max_length=100, verbose_name="Oído Izquierdo", default="Conducto permeable, Membrana timpánica íntegra")
    
    # Nariz (Rinoscopia)
    rinoscopia = models.TextField(verbose_name="Fosas Nasales / Cornetes", blank=True)
    tabique = models.CharField(max_length=50, choices=[('CENTRADO', 'Centrado'), ('DESVIADO_D', 'Desviado Derecha'), ('DESVIADO_I', 'Desviado Izquierda')], default='CENTRADO')
    
    # Garganta (Orofaringe)
    orofaringe = models.TextField(verbose_name="Boca / Faringe / Amígdalas", blank=True)
    
    # Estudios Extra
    audiometria = models.CharField(max_length=100, verbose_name="Resumen Audiometría", blank=True)

    def __str__(self):
        return f"ORL - {self.historia_clinica.paciente}"
    
class HistoriaTraumatologia(models.Model):
    historia_clinica = models.OneToOneField(HistoriaClinica, on_delete=models.CASCADE, related_name='traumatologia')
    
    zona_afectada = models.CharField(max_length=100, verbose_name="Zona Afectada (Ej: Rodilla Der)")
    mecanismo_lesion = models.TextField(verbose_name="Mecanismo de Lesión (Caída, Deportivo...)", blank=True)
    
    # Examen Físico Específico
    movilidad = models.CharField(max_length=100, verbose_name="Arcos de Movilidad (ROM)", default="Completos / Sin limitación")
    fuerza_muscular = models.CharField(max_length=50, verbose_name="Fuerza (Daniels 1-5)", default="5/5 (Normal)")
    sensibilidad = models.CharField(max_length=100, verbose_name="Sensibilidad / Reflejos", default="Conservada")
    
    pruebas_especiales = models.TextField(verbose_name="Pruebas Específicas (Cajón, Lachman...)", blank=True)
    plan_rehabilitacion = models.TextField(verbose_name="Plan de Rehabilitación / Fisioterapia", blank=True)

    def __str__(self):
        return f"Trauma - {self.historia_clinica.paciente}"
    
# --- HISTORIA CLÍNICA: GASTROENTEROLOGÍA ---
class HistoriaGastro(models.Model):
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='gastro')
    dolor_abdominal = models.TextField(verbose_name="Localización y tipo de dolor", blank=True, null=True)
    habito_intestinal = models.CharField(max_length=100, verbose_name="Hábito intestinal (Frecuencia/Consistencia)", blank=True, null=True)
    endoscopia_previa = models.TextField(verbose_name="Resultados de endoscopias/colonoscopias previas", blank=True, null=True)
    reflejo_hepatoyugular = models.BooleanField(default=False)
    observaciones_digestivas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Gastro - {self.historia_clinica}"

# --- HISTORIA CLÍNICA: PSIQUIATRÍA ---
class HistoriaPsiquiatria(models.Model):
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='psiquiatria')
    examen_mental = models.TextField(verbose_name="Descripción del examen mental actual", blank=True, null=True)
    ideacion_suicida = models.BooleanField(default=False, verbose_name="Presencia de ideación suicida")
    medicacion_psicotropica = models.TextField(verbose_name="Medicamentos actuales y dosis", blank=True, null=True)
    antecedentes_psiquiatricos = models.TextField(blank=True, null=True)
    estado_conciencia = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Psiquiatría - {self.historia_clinica}"

# --- HISTORIA CLÍNICA: REUMATOLOGÍA ---
class HistoriaReumatologia(models.Model):
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='reumatologia')
    rigidez_matutina = models.CharField(max_length=100, verbose_name="Duración de rigidez matutina (min/horas)", blank=True, null=True)
    articulaciones_afectadas = models.TextField(verbose_name="Articulaciones con dolor o inflamación", blank=True, null=True)
    factor_reumatoide = models.CharField(max_length=50, verbose_name="Resultado Factor Reumatoide / Anti-CCP", blank=True, null=True)
    capacidad_funcional = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Reumatología - {self.historia_clinica}"

# --- HISTORIA CLÍNICA: GERIATRÍA ---
class HistoriaGeriatria(models.Model):
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='geriatria')
    escala_kartz = models.CharField(max_length=50, verbose_name="Escala de Katz (Actividades vida diaria)", blank=True, null=True)
    deterioro_cognitivo = models.TextField(verbose_name="Evaluación cognitiva (Ej: Minimental)", blank=True, null=True)
    polifarmacia = models.TextField(verbose_name="Lista de todos los fármacos consumidos", blank=True, null=True)
    riesgo_caidas = models.BooleanField(default=False, verbose_name="Antecedentes o riesgo de caídas")
    soporte_familiar = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Geriatría - {self.historia_clinica}"
    
# --- HISTORIA CLÍNICA: NEUROLOGÍA ---
class HistoriaNeurologia(models.Model):
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='neurologia')
    escala_glasgow = models.CharField(max_length=20, verbose_name="Escala de Glasgow (O+V+M)", blank=True, null=True)
    pares_craneales = models.TextField(verbose_name="Exploración de pares craneales", blank=True, null=True)
    fuerza_motora = models.CharField(max_length=100, verbose_name="Fuerza motora MMSS/MMII", blank=True, null=True)
    reflejos = models.CharField(max_length=100, verbose_name="Reflejos osteotendinosos", blank=True, null=True)
    coordinacion = models.CharField(max_length=100, verbose_name="Coordinación y equilibrio", blank=True, null=True)
    sensibilidad_neuro = models.CharField(max_length=100, verbose_name="Sensibilidad", blank=True, null=True)
    neuroimagen = models.TextField(verbose_name="TAC / RMN / EEG (hallazgos)", blank=True, null=True)
    escala_nihss = models.CharField(max_length=20, verbose_name="Escala NIHSS (si aplica ACV)", blank=True, null=True)

    def __str__(self):
        return f"Neurología - {self.historia_clinica}"


# --- HISTORIA CLÍNICA: ENDOCRINOLOGÍA ---
class HistoriaEndocrinologia(models.Model):
    TIPO_DM = [('DM1','DM Tipo 1'),('DM2','DM Tipo 2'),('GEST','Gestacional'),('OTRO','Otro / No aplica')]
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='endocrinologia')
    tipo_diabetes = models.CharField(max_length=10, choices=TIPO_DM, default='OTRO', verbose_name="Tipo de Diabetes")
    glucosa_ayunas = models.CharField(max_length=20, verbose_name="Glucosa en ayunas (mg/dL)", blank=True, null=True)
    hba1c = models.CharField(max_length=10, verbose_name="HbA1c (%)", blank=True, null=True)
    insulina_basal = models.CharField(max_length=50, verbose_name="Insulina / dosis actual", blank=True, null=True)
    tsh = models.CharField(max_length=20, verbose_name="TSH (mUI/L)", blank=True, null=True)
    t3_t4 = models.CharField(max_length=50, verbose_name="T3 / T4 libre", blank=True, null=True)
    cortisol = models.CharField(max_length=20, verbose_name="Cortisol sérico", blank=True, null=True)
    objetivos_terapeuticos = models.TextField(verbose_name="Objetivos terapéuticos / Plan", blank=True, null=True)

    def __str__(self):
        return f"Endocrinología - {self.historia_clinica}"


# --- HISTORIA CLÍNICA: MEDICINA INTERNA ---
class HistoriaMedicinaInterna(models.Model):
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='medicina_interna')
    mucosas = models.CharField(max_length=100, verbose_name="Mucosas", blank=True, null=True)
    ganglios = models.CharField(max_length=100, verbose_name="Adenopatías / Ganglios", blank=True, null=True)
    tiroides_examen = models.CharField(max_length=100, verbose_name="Tiroides al examen", blank=True, null=True)
    examen_pulmonar = models.TextField(verbose_name="Examen pulmonar (auscultación)", blank=True, null=True)
    examen_cardiaco = models.TextField(verbose_name="Examen cardíaco (auscultación)", blank=True, null=True)
    examen_abdominal = models.TextField(verbose_name="Examen abdominal", blank=True, null=True)
    examen_extremidades = models.TextField(verbose_name="Extremidades / Edemas", blank=True, null=True)
    examenes_laboratorio = models.TextField(verbose_name="Laboratorio / Imagen relevante", blank=True, null=True)

    def __str__(self):
        return f"Medicina Interna - {self.historia_clinica}"


# --- HISTORIA CLÍNICA: CIRUGÍA GENERAL ---
class HistoriaCirugia(models.Model):
    ASA = [('I','ASA I - Sano'),('II','ASA II - Enfermedad leve'),('III','ASA III - Enfermedad grave'),('IV','ASA IV - Riesgo vital'),('V','ASA V - Moribundo')]
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='cirugia')
    tipo_cirugia = models.CharField(max_length=150, verbose_name="Tipo / Nombre de la cirugía", blank=True, null=True)
    clasificacion_asa = models.CharField(max_length=5, choices=ASA, default='I', verbose_name="Clasificación ASA")
    hallazgos_intraop = models.TextField(verbose_name="Hallazgos intraoperatorios", blank=True, null=True)
    tecnica_quirurgica = models.TextField(verbose_name="Técnica quirúrgica empleada", blank=True, null=True)
    complicaciones_qx = models.TextField(verbose_name="Complicaciones", blank=True, null=True)
    plan_postoperatorio = models.TextField(verbose_name="Plan postoperatorio / Indicaciones", blank=True, null=True)
    fecha_cirugia = models.DateField(verbose_name="Fecha de cirugía", null=True, blank=True)

    def __str__(self):
        return f"Cirugía General - {self.historia_clinica}"


# --- HISTORIA CLÍNICA: UROLOGÍA ---
class HistoriaUrologia(models.Model):
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='urologia')
    sintomas_miccionales = models.CharField(max_length=100, verbose_name="Síntomas miccionales / Score IPSS", blank=True, null=True)
    psa = models.CharField(max_length=20, verbose_name="PSA total (ng/mL)", blank=True, null=True)
    creatinina_uro = models.CharField(max_length=20, verbose_name="Creatinina sérica (mg/dL)", blank=True, null=True)
    urocultivo = models.CharField(max_length=100, verbose_name="Urocultivo / Uroanálisis", blank=True, null=True)
    ecografia = models.TextField(verbose_name="Ecografía renal / Prostática (hallazgos)", blank=True, null=True)
    residuo_postmiccional = models.CharField(max_length=50, verbose_name="Residuo postmiccional (mL)", blank=True, null=True)
    cistoscopia = models.TextField(verbose_name="Cistoscopia (hallazgos)", blank=True, null=True)

    def __str__(self):
        return f"Urología - {self.historia_clinica}"


# --- HISTORIA CLÍNICA: NEUMOLOGÍA ---
class HistoriaNeurologia_Neumologia(models.Model):
    PATRON = [('NORMAL','Normal'),('OBSTR','Obstructivo'),('REST','Restrictivo'),('MIXTO','Mixto')]
    TABACO = [('NO','No fumador'),('EX','Ex-fumador'),('SI','Fumador activo')]
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='neumologia')
    saturacion_o2 = models.CharField(max_length=10, verbose_name="Saturación O2 (%)", blank=True, null=True)
    fev1 = models.CharField(max_length=20, verbose_name="FEV1 (L / %)", blank=True, null=True)
    fvc = models.CharField(max_length=20, verbose_name="FVC (L / %)", blank=True, null=True)
    relacion_fev1_fvc = models.CharField(max_length=20, verbose_name="Relación FEV1/FVC", blank=True, null=True)
    patron_espirometrico = models.CharField(max_length=10, choices=PATRON, default='NORMAL', verbose_name="Patrón espirométrico")
    tabaquismo = models.CharField(max_length=5, choices=TABACO, default='NO', verbose_name="Tabaquismo")
    indice_paquete_anio = models.CharField(max_length=20, verbose_name="Índice paquete/año", blank=True, null=True)
    rx_tac_torax = models.TextField(verbose_name="Rx / TAC de tórax (hallazgos)", blank=True, null=True)

    class Meta:
        verbose_name = "Historia Neumología"

    def __str__(self):
        return f"Neumología - {self.historia_clinica}"


# --- HISTORIA CLÍNICA: NEFROLOGÍA ---
class HistoriaNefrologia(models.Model):
    ESTADIO_ERC = [('1','ERC 1 (TFG≥90)'),('2','ERC 2 (TFG 60-89)'),('3A','ERC 3a (TFG 45-59)'),
                   ('3B','ERC 3b (TFG 30-44)'),('4','ERC 4 (TFG 15-29)'),('5','ERC 5 (TFG<15)'),('5D','ERC 5D - Diálisis')]
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='nefrologia')
    creatinina_nef = models.CharField(max_length=20, verbose_name="Creatinina sérica (mg/dL)", blank=True, null=True)
    tfg = models.CharField(max_length=20, verbose_name="TFG estimada (mL/min/1.73m²)", blank=True, null=True)
    proteinuria = models.CharField(max_length=50, verbose_name="Proteinuria (mg/24h o ratio)", blank=True, null=True)
    urea_bun = models.CharField(max_length=20, verbose_name="Urea / BUN", blank=True, null=True)
    estadio_erc = models.CharField(max_length=5, choices=ESTADIO_ERC, default='1', verbose_name="Estadio ERC")
    en_hemodialisis = models.BooleanField(default=False, verbose_name="En hemodiálisis")
    acceso_vascular = models.CharField(max_length=100, verbose_name="Acceso vascular", blank=True, null=True)
    control_pa = models.CharField(max_length=50, verbose_name="Control de PA", blank=True, null=True)

    def __str__(self):
        return f"Nefrología - {self.historia_clinica}"


# --- HISTORIA CLÍNICA: MEDICINA DE EMERGENCIAS ---
class HistoriaEmergencias(models.Model):
    TRIAGE = [('1','Rojo - Nivel 1 (Crítico)'),('2','Naranja - Nivel 2 (Urgente)'),
              ('3','Amarillo - Nivel 3 (Menos urgente)'),('4','Verde - Nivel 4 (No urgente)'),('5','Azul - Nivel 5 (Sin urgencia)')]
    DESTINO = [('ALTA','Alta domiciliaria'),('HOSP','Hospitalización'),('UCI','UCI / Cuidados intensivos'),
               ('CX','Quirófano'),('TRASL','Traslado'),('FALL','Fallecimiento')]
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='emergencias')
    nivel_triage = models.CharField(max_length=3, choices=TRIAGE, default='3', verbose_name="Nivel de Triage (MSP)")
    mecanismo_trauma = models.TextField(verbose_name="Mecanismo de lesión / Causa consulta emergencia", blank=True, null=True)
    glasgow_emergencia = models.CharField(max_length=20, verbose_name="Glasgow (O+V+M)", blank=True, null=True)
    via_aerea = models.CharField(max_length=100, verbose_name="A - Vía aérea", blank=True, null=True)
    respiracion_emerg = models.CharField(max_length=100, verbose_name="B - Respiración / Ventilación", blank=True, null=True)
    circulacion_emerg = models.CharField(max_length=100, verbose_name="C - Circulación / Hemorragia", blank=True, null=True)
    procedimientos = models.TextField(verbose_name="Procedimientos realizados", blank=True, null=True)
    medicacion_urgente = models.TextField(verbose_name="Medicación administrada en emergencia", blank=True, null=True)
    destino_paciente = models.CharField(max_length=10, choices=DESTINO, default='ALTA', verbose_name="Destino del paciente")

    def __str__(self):
        return f"Emergencias - {self.historia_clinica}"


class Receta(models.Model):
    # Relación con la historia clínica (una historia puede tener una receta)
    historia_clinica = models.OneToOneField('HistoriaClinica', on_delete=models.CASCADE, related_name='receta')
    
    # El contenido principal
    prescripcion = models.TextField(help_text="Lista de medicamentos y dosis")
    indicaciones_generales = models.TextField(blank=True, null=True, help_text="Reposo, dieta, etc.")
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receta - {self.historia_clinica.paciente.usuario.get_full_name()}"
    
class Triaje(models.Model):
    paciente = models.ForeignKey('paciente.Paciente', on_delete=models.CASCADE)
    cita = models.OneToOneField('citas.Cita', on_delete=models.CASCADE, related_name='triaje')
    peso = models.DecimalField(max_digits=5, decimal_places=2, help_text="Peso en kg")
    talla = models.DecimalField(max_digits=5, decimal_places=2, help_text="Talla en cm")
    presion_arterial = models.CharField(max_length=20) # Ejemplo: 120/80
    frecuencia_cardiaca = models.IntegerField(help_text="LPM")
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, help_text="°C")
    saturacion_oxigeno = models.IntegerField(help_text="% SpO2")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Triaje - {self.paciente} - {self.fecha_registro.date()}"


class CodigoCIE10(models.Model):
    codigo = models.CharField(max_length=10, unique=True, db_index=True, verbose_name="Código CIE-10")
    descripcion = models.CharField(max_length=300, db_index=True, verbose_name="Descripción")
    capitulo = models.CharField(max_length=120, blank=True, verbose_name="Capítulo")

    class Meta:
        verbose_name = "Código CIE-10"
        verbose_name_plural = "Códigos CIE-10"
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"