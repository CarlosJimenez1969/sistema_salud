from django.db import models
from paciente.models import Paciente
from medico.models import Medico

class HistoriaClinica(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='historias')
    medico = models.ForeignKey(Medico, on_delete=models.PROTECT, related_name='historias_creadas')
    fecha_atencion = models.DateTimeField(auto_now_add=True)
    
    # --- SECCIÓN 1: MOTIVO Y ENFERMEDAD (MSP) ---
    motivo_consulta = models.TextField(help_text="Motivo por el cual viene el paciente")
    enfermedad_actual = models.TextField(help_text="Descripción detallada de la molestia")
    
    # --- SECCIÓN 2: SIGNOS VITALES ---
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, help_text="°C", null=True, blank=True)
    presion_arterial = models.CharField(max_length=20, help_text="Ej: 120/80", null=True, blank=True)
    pulso = models.IntegerField(help_text="Latidos por minuto", null=True, blank=True)
    peso = models.DecimalField(max_digits=5, decimal_places=2, help_text="Kg", null=True, blank=True)
    altura = models.DecimalField(max_digits=5, decimal_places=2, help_text="Metros o CM", null=True, blank=True)
    
    # --- SECCIÓN 3: EXAMEN Y DIAGNÓSTICO ---
    examen_fisico = models.TextField(help_text="Hallazgos del examen físico")
    diagnostico = models.TextField(help_text="Diagnóstico Presuntivo o Definitivo (CIE-10)")
    tratamiento = models.TextField(help_text="Indicaciones y medicamentos")
    
    def __str__(self):
        return f"Historia {self.id} - {self.paciente} ({self.fecha_atencion.date()})"

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
    proxima_cita = models.DateField(null=True, blank=True, verbose_name="Próxima Cita / Control")

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