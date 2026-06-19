"""
Carga el catálogo CIE-10 (Clasificación Internacional de Enfermedades, 10a revisión)
en español a la base de datos.

Uso:
    python manage.py cargar_cie10                  # Carga el set base embebido (~800 códigos)
    python manage.py cargar_cie10 --csv ruta.csv   # Carga adicional desde CSV
    python manage.py cargar_cie10 --limpiar        # Limpia antes de cargar

CSV esperado: codigo,descripcion,capitulo (header obligatorio).
"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from historia.models import CodigoCIE10


# ============================================================
# CATÁLOGO BASE — Códigos CIE-10 más usados en consulta ambulatoria
# Organizado por capítulos OMS/MSP Ecuador
# ============================================================
CIE10_BASE = [
    # === CAP I — A00-B99: Infecciosas y parasitarias ===
    ("A00.9", "Cólera, no especificado", "I. Infecciosas y parasitarias"),
    ("A01.0", "Fiebre tifoidea", "I. Infecciosas y parasitarias"),
    ("A06.0", "Disentería amebiana aguda", "I. Infecciosas y parasitarias"),
    ("A08.0", "Enteritis debida a rotavirus", "I. Infecciosas y parasitarias"),
    ("A08.4", "Infección intestinal viral, sin otra especificación", "I. Infecciosas y parasitarias"),
    ("A09.X", "Diarrea y gastroenteritis de presunto origen infeccioso", "I. Infecciosas y parasitarias"),
    ("A15.0", "Tuberculosis del pulmón, confirmada por hallazgo microscópico", "I. Infecciosas y parasitarias"),
    ("A15.9", "Tuberculosis respiratoria no especificada", "I. Infecciosas y parasitarias"),
    ("A16.2", "Tuberculosis de pulmón, sin mención de confirmación bacteriológica o histológica", "I. Infecciosas y parasitarias"),
    ("A41.9", "Septicemia, no especificada", "I. Infecciosas y parasitarias"),
    ("A49.9", "Infección bacteriana, no especificada", "I. Infecciosas y parasitarias"),
    ("A54.0", "Infección gonocócica del tracto genitourinario inferior sin absceso periuretral o de glándulas accesorias", "I. Infecciosas y parasitarias"),
    ("A60.0", "Infección de genitales y tracto genitourinario por virus del herpes", "I. Infecciosas y parasitarias"),
    ("A64.X", "Enfermedad de transmisión sexual no especificada", "I. Infecciosas y parasitarias"),
    ("A87.9", "Meningitis viral, no especificada", "I. Infecciosas y parasitarias"),
    ("A90.X", "Fiebre del dengue (dengue clásico)", "I. Infecciosas y parasitarias"),
    ("A91.X", "Fiebre del dengue hemorrágico", "I. Infecciosas y parasitarias"),
    ("A92.0", "Enfermedad por virus Chikungunya", "I. Infecciosas y parasitarias"),
    ("A92.5", "Enfermedad por virus del Zika", "I. Infecciosas y parasitarias"),
    ("B00.9", "Infección debida a herpes virus, no especificada", "I. Infecciosas y parasitarias"),
    ("B01.9", "Varicela sin complicaciones", "I. Infecciosas y parasitarias"),
    ("B02.9", "Herpes zoster sin complicaciones", "I. Infecciosas y parasitarias"),
    ("B05.9", "Sarampión sin complicaciones", "I. Infecciosas y parasitarias"),
    ("B06.9", "Rubéola sin complicaciones", "I. Infecciosas y parasitarias"),
    ("B08.4", "Estomatitis vesicular enteroviral con exantema", "I. Infecciosas y parasitarias"),
    ("B15.9", "Hepatitis aguda tipo A sin coma hepático", "I. Infecciosas y parasitarias"),
    ("B16.9", "Hepatitis aguda tipo B sin agente delta y sin coma hepático", "I. Infecciosas y parasitarias"),
    ("B18.1", "Hepatitis viral tipo B crónica, sin agente delta", "I. Infecciosas y parasitarias"),
    ("B18.2", "Hepatitis viral tipo C crónica", "I. Infecciosas y parasitarias"),
    ("B20.9", "Enfermedad por VIH resultante en enfermedad infecciosa o parasitaria no especificada", "I. Infecciosas y parasitarias"),
    ("B24.X", "Enfermedad por virus de la inmunodeficiencia humana [VIH], sin otra especificación", "I. Infecciosas y parasitarias"),
    ("B27.9", "Mononucleosis infecciosa, sin otra especificación", "I. Infecciosas y parasitarias"),
    ("B30.9", "Conjuntivitis viral, sin otra especificación", "I. Infecciosas y parasitarias"),
    ("B34.9", "Infección viral, no especificada", "I. Infecciosas y parasitarias"),
    ("B35.0", "Tiña de la barba y del cuero cabelludo", "I. Infecciosas y parasitarias"),
    ("B35.3", "Tiña de los pies", "I. Infecciosas y parasitarias"),
    ("B35.4", "Tiña corporal", "I. Infecciosas y parasitarias"),
    ("B36.0", "Pitiriasis versicolor", "I. Infecciosas y parasitarias"),
    ("B37.0", "Estomatitis candidiásica", "I. Infecciosas y parasitarias"),
    ("B37.3", "Candidiasis de la vulva y de la vagina", "I. Infecciosas y parasitarias"),
    ("B37.9", "Candidiasis, no especificada", "I. Infecciosas y parasitarias"),
    ("B50.9", "Paludismo por Plasmodium falciparum, sin otra especificación", "I. Infecciosas y parasitarias"),
    ("B54.X", "Paludismo no especificado", "I. Infecciosas y parasitarias"),
    ("B55.1", "Leishmaniasis cutánea", "I. Infecciosas y parasitarias"),
    ("B55.2", "Leishmaniasis mucocutánea", "I. Infecciosas y parasitarias"),
    ("B57.5", "Enfermedad de Chagas con compromiso de otros órganos", "I. Infecciosas y parasitarias"),
    ("B76.9", "Anquilostomiasis, no especificada", "I. Infecciosas y parasitarias"),
    ("B77.9", "Ascariasis, no especificada", "I. Infecciosas y parasitarias"),
    ("B80.X", "Oxiuriasis (enterobiasis)", "I. Infecciosas y parasitarias"),
    ("B82.0", "Helmintiasis intestinal, no especificada", "I. Infecciosas y parasitarias"),
    ("B86.X", "Escabiosis (sarna)", "I. Infecciosas y parasitarias"),
    ("B87.9", "Miasis no especificada", "I. Infecciosas y parasitarias"),
    ("B99.X", "Enfermedades infecciosas, otras y las no especificadas", "I. Infecciosas y parasitarias"),

    # === CAP II — C00-D48: Tumores ===
    ("C16.9", "Tumor maligno del estómago, parte no especificada", "II. Tumores [Neoplasias]"),
    ("C18.9", "Tumor maligno del colon, parte no especificada", "II. Tumores [Neoplasias]"),
    ("C34.9", "Tumor maligno de los bronquios o del pulmón, parte no especificada", "II. Tumores [Neoplasias]"),
    ("C50.9", "Tumor maligno de la mama, parte no especificada", "II. Tumores [Neoplasias]"),
    ("C53.9", "Tumor maligno del cuello del útero, sin otra especificación", "II. Tumores [Neoplasias]"),
    ("C56.X", "Tumor maligno del ovario", "II. Tumores [Neoplasias]"),
    ("C61.X", "Tumor maligno de la próstata", "II. Tumores [Neoplasias]"),
    ("C73.X", "Tumor maligno de la glándula tiroidea", "II. Tumores [Neoplasias]"),
    ("C80.9", "Tumor maligno de sitios no especificados", "II. Tumores [Neoplasias]"),
    ("D17.9", "Tumor lipomatoso benigno, sin otra especificación", "II. Tumores [Neoplasias]"),
    ("D22.9", "Nevus melanocítico, sitio no especificado", "II. Tumores [Neoplasias]"),
    ("D24.X", "Tumor benigno de la mama", "II. Tumores [Neoplasias]"),
    ("D25.9", "Leiomioma del útero, sin otra especificación", "II. Tumores [Neoplasias]"),
    ("D36.9", "Tumor benigno de sitio no especificado", "II. Tumores [Neoplasias]"),

    # === CAP III — D50-D89: Sangre y órganos hematopoyéticos ===
    ("D50.9", "Anemia por deficiencia de hierro sin otra especificación", "III. Sangre y órganos hematopoyéticos"),
    ("D51.0", "Anemia por deficiencia de vitamina B12 debida a deficiencia de factor intrínseco", "III. Sangre y órganos hematopoyéticos"),
    ("D52.9", "Anemia por deficiencia de folatos, sin otra especificación", "III. Sangre y órganos hematopoyéticos"),
    ("D53.9", "Anemia nutricional, no especificada", "III. Sangre y órganos hematopoyéticos"),
    ("D56.1", "Talasemia beta", "III. Sangre y órganos hematopoyéticos"),
    ("D57.1", "Anemia de células falciformes sin crisis", "III. Sangre y órganos hematopoyéticos"),
    ("D64.9", "Anemia, no especificada", "III. Sangre y órganos hematopoyéticos"),
    ("D69.6", "Trombocitopenia, no especificada", "III. Sangre y órganos hematopoyéticos"),
    ("D72.8", "Otros trastornos especificados de los leucocitos", "III. Sangre y órganos hematopoyéticos"),
    ("D75.9", "Enfermedad de la sangre y de los órganos hematopoyéticos, no especificada", "III. Sangre y órganos hematopoyéticos"),

    # === CAP IV — E00-E90: Endocrinas, nutricionales y metabólicas ===
    ("E03.9", "Hipotiroidismo, no especificado", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E04.0", "Bocio difuso no tóxico", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E05.9", "Tirotoxicosis, no especificada", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E06.3", "Tiroiditis autoinmune", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E10.9", "Diabetes mellitus tipo 1 sin complicaciones", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E11.9", "Diabetes mellitus tipo 2 sin complicaciones", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E11.2", "Diabetes mellitus tipo 2 con complicaciones renales", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E11.3", "Diabetes mellitus tipo 2 con complicaciones oftálmicas", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E11.4", "Diabetes mellitus tipo 2 con complicaciones neurológicas", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E11.5", "Diabetes mellitus tipo 2 con complicaciones circulatorias periféricas", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E13.9", "Otras diabetes mellitus especificadas, sin complicaciones", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E14.9", "Diabetes mellitus, no especificada, sin complicaciones", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E16.2", "Hipoglicemia, no especificada", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E27.4", "Insuficiencia adrenocortical, no especificada", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E28.2", "Síndrome de ovario poliquístico", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E34.3", "Talla baja, no clasificada en otra parte", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E40.X", "Kwashiorkor", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E44.0", "Desnutrición proteicocalórica moderada", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E46.X", "Desnutrición proteicocalórica, no especificada", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E55.9", "Deficiencia de vitamina D, no especificada", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E61.1", "Deficiencia de hierro", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E63.9", "Deficiencia nutricional, no especificada", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E66.0", "Obesidad debida a exceso de calorías", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E66.9", "Obesidad, no especificada", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E78.0", "Hipercolesterolemia pura", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E78.1", "Hipergliceridemia pura", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E78.2", "Hiperlipidemia mixta", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E78.5", "Hiperlipidemia, no especificada", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E79.0", "Hiperuricemia sin signos de artritis inflamatoria y enfermedad tofácea", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E86.X", "Depleción del volumen", "IV. Endocrinas, nutricionales y metabólicas"),
    ("E87.6", "Hipopotasemia", "IV. Endocrinas, nutricionales y metabólicas"),

    # === CAP V — F00-F99: Mentales y del comportamiento ===
    ("F03.X", "Demencia, no especificada", "V. Trastornos mentales y del comportamiento"),
    ("F10.2", "Trastornos mentales y del comportamiento debido al uso de alcohol, síndrome de dependencia", "V. Trastornos mentales y del comportamiento"),
    ("F17.2", "Trastornos mentales y del comportamiento debido al uso de tabaco, síndrome de dependencia", "V. Trastornos mentales y del comportamiento"),
    ("F19.2", "Trastornos mentales debido al uso de múltiples drogas, síndrome de dependencia", "V. Trastornos mentales y del comportamiento"),
    ("F20.9", "Esquizofrenia, no especificada", "V. Trastornos mentales y del comportamiento"),
    ("F31.9", "Trastorno afectivo bipolar, no especificado", "V. Trastornos mentales y del comportamiento"),
    ("F32.0", "Episodio depresivo leve", "V. Trastornos mentales y del comportamiento"),
    ("F32.1", "Episodio depresivo moderado", "V. Trastornos mentales y del comportamiento"),
    ("F32.2", "Episodio depresivo grave sin síntomas psicóticos", "V. Trastornos mentales y del comportamiento"),
    ("F32.9", "Episodio depresivo, no especificado", "V. Trastornos mentales y del comportamiento"),
    ("F33.9", "Trastorno depresivo recurrente, no especificado", "V. Trastornos mentales y del comportamiento"),
    ("F41.0", "Trastorno de pánico (ansiedad paroxística episódica)", "V. Trastornos mentales y del comportamiento"),
    ("F41.1", "Trastorno de ansiedad generalizada", "V. Trastornos mentales y del comportamiento"),
    ("F41.2", "Trastorno mixto ansioso-depresivo", "V. Trastornos mentales y del comportamiento"),
    ("F41.9", "Trastorno de ansiedad, no especificado", "V. Trastornos mentales y del comportamiento"),
    ("F43.0", "Reacción al estrés agudo", "V. Trastornos mentales y del comportamiento"),
    ("F43.1", "Trastorno por estrés postraumático", "V. Trastornos mentales y del comportamiento"),
    ("F43.2", "Trastornos de adaptación", "V. Trastornos mentales y del comportamiento"),
    ("F45.0", "Trastorno de somatización", "V. Trastornos mentales y del comportamiento"),
    ("F50.0", "Anorexia nerviosa", "V. Trastornos mentales y del comportamiento"),
    ("F50.2", "Bulimia nerviosa", "V. Trastornos mentales y del comportamiento"),
    ("F51.0", "Insomnio no orgánico", "V. Trastornos mentales y del comportamiento"),
    ("F90.0", "Trastorno de la actividad y de la atención", "V. Trastornos mentales y del comportamiento"),
    ("F99.X", "Trastorno mental, no especificado", "V. Trastornos mentales y del comportamiento"),

    # === CAP VI — G00-G99: Sistema nervioso ===
    ("G35.X", "Esclerosis múltiple", "VI. Sistema nervioso"),
    ("G40.9", "Epilepsia, tipo no especificado", "VI. Sistema nervioso"),
    ("G43.0", "Migraña sin aura (migraña común)", "VI. Sistema nervioso"),
    ("G43.1", "Migraña con aura (migraña clásica)", "VI. Sistema nervioso"),
    ("G43.9", "Migraña, no especificada", "VI. Sistema nervioso"),
    ("G44.2", "Cefalea tipo tensional", "VI. Sistema nervioso"),
    ("G47.0", "Trastornos del inicio y del mantenimiento del sueño (insomnios)", "VI. Sistema nervioso"),
    ("G47.3", "Apnea del sueño", "VI. Sistema nervioso"),
    ("G50.0", "Neuralgia del trigémino", "VI. Sistema nervioso"),
    ("G54.1", "Trastornos del plexo lumbosacro", "VI. Sistema nervioso"),
    ("G55.1", "Compresiones de las raíces y plexos nerviosos en trastornos de los discos intervertebrales", "VI. Sistema nervioso"),
    ("G56.0", "Síndrome del túnel carpiano", "VI. Sistema nervioso"),
    ("G62.9", "Polineuropatía, no especificada", "VI. Sistema nervioso"),
    ("G81.9", "Hemiplejía, no especificada", "VI. Sistema nervioso"),
    ("G93.1", "Daño cerebral anóxico, no clasificado en otra parte", "VI. Sistema nervioso"),

    # === CAP VII — H00-H59: Ojo y anexos ===
    ("H00.0", "Orzuelo y otras inflamaciones profundas del párpado", "VII. Ojo y anexos"),
    ("H10.0", "Conjuntivitis mucopurulenta", "VII. Ojo y anexos"),
    ("H10.1", "Conjuntivitis atópica aguda", "VII. Ojo y anexos"),
    ("H10.9", "Conjuntivitis, no especificada", "VII. Ojo y anexos"),
    ("H11.0", "Pterigión", "VII. Ojo y anexos"),
    ("H16.0", "Úlcera de la córnea", "VII. Ojo y anexos"),
    ("H25.9", "Catarata senil, no especificada", "VII. Ojo y anexos"),
    ("H35.0", "Retinopatía de fondo y cambios vasculares retinianos", "VII. Ojo y anexos"),
    ("H40.9", "Glaucoma, no especificado", "VII. Ojo y anexos"),
    ("H52.0", "Hipermetropía", "VII. Ojo y anexos"),
    ("H52.1", "Miopía", "VII. Ojo y anexos"),
    ("H52.2", "Astigmatismo", "VII. Ojo y anexos"),
    ("H52.4", "Presbicia", "VII. Ojo y anexos"),

    # === CAP VIII — H60-H95: Oído y apófisis mastoides ===
    ("H60.9", "Otitis externa, no especificada", "VIII. Oído y apófisis mastoides"),
    ("H65.0", "Otitis media aguda serosa", "VIII. Oído y apófisis mastoides"),
    ("H66.0", "Otitis media supurativa aguda", "VIII. Oído y apófisis mastoides"),
    ("H66.9", "Otitis media, no especificada", "VIII. Oído y apófisis mastoides"),
    ("H81.0", "Enfermedad de Ménière", "VIII. Oído y apófisis mastoides"),
    ("H81.1", "Vértigo paroxístico benigno", "VIII. Oído y apófisis mastoides"),
    ("H90.5", "Hipoacusia neurosensorial, no especificada", "VIII. Oído y apófisis mastoides"),
    ("H91.9", "Pérdida de la audición, no especificada", "VIII. Oído y apófisis mastoides"),
    ("H93.1", "Tinnitus", "VIII. Oído y apófisis mastoides"),

    # === CAP IX — I00-I99: Sistema circulatorio ===
    ("I10.X", "Hipertensión esencial (primaria)", "IX. Sistema circulatorio"),
    ("I11.0", "Enfermedad cardíaca hipertensiva con insuficiencia cardíaca (congestiva)", "IX. Sistema circulatorio"),
    ("I11.9", "Enfermedad cardíaca hipertensiva sin insuficiencia cardíaca (congestiva)", "IX. Sistema circulatorio"),
    ("I12.0", "Enfermedad renal hipertensiva con insuficiencia renal", "IX. Sistema circulatorio"),
    ("I15.9", "Hipertensión secundaria, no especificada", "IX. Sistema circulatorio"),
    ("I20.0", "Angina inestable", "IX. Sistema circulatorio"),
    ("I20.9", "Angina de pecho, no especificada", "IX. Sistema circulatorio"),
    ("I21.9", "Infarto agudo de miocardio, sin otra especificación", "IX. Sistema circulatorio"),
    ("I25.1", "Enfermedad aterosclerótica del corazón", "IX. Sistema circulatorio"),
    ("I25.9", "Enfermedad isquémica crónica del corazón, no especificada", "IX. Sistema circulatorio"),
    ("I42.0", "Cardiomiopatía dilatada", "IX. Sistema circulatorio"),
    ("I48.X", "Fibrilación y aleteo auricular", "IX. Sistema circulatorio"),
    ("I49.9", "Arritmia cardíaca, no especificada", "IX. Sistema circulatorio"),
    ("I50.0", "Insuficiencia cardíaca congestiva", "IX. Sistema circulatorio"),
    ("I50.9", "Insuficiencia cardíaca, no especificada", "IX. Sistema circulatorio"),
    ("I63.9", "Infarto cerebral, no especificado", "IX. Sistema circulatorio"),
    ("I64.X", "Accidente vascular encefálico agudo, no especificado", "IX. Sistema circulatorio"),
    ("I70.2", "Aterosclerosis de las arterias distales", "IX. Sistema circulatorio"),
    ("I73.9", "Enfermedad vascular periférica, no especificada", "IX. Sistema circulatorio"),
    ("I80.0", "Flebitis y tromboflebitis de vasos superficiales de los miembros inferiores", "IX. Sistema circulatorio"),
    ("I83.9", "Várices de los miembros inferiores sin úlcera ni inflamación", "IX. Sistema circulatorio"),
    ("I84.9", "Hemorroides, sin complicaciones, no especificadas", "IX. Sistema circulatorio"),
    ("I88.9", "Linfadenitis inespecífica, no especificada", "IX. Sistema circulatorio"),
    ("I95.9", "Hipotensión, no especificada", "IX. Sistema circulatorio"),

    # === CAP X — J00-J99: Sistema respiratorio ===
    ("J00.X", "Rinofaringitis aguda (resfriado común)", "X. Sistema respiratorio"),
    ("J01.9", "Sinusitis aguda, no especificada", "X. Sistema respiratorio"),
    ("J02.0", "Faringitis estreptocócica", "X. Sistema respiratorio"),
    ("J02.9", "Faringitis aguda, no especificada", "X. Sistema respiratorio"),
    ("J03.9", "Amigdalitis aguda, no especificada", "X. Sistema respiratorio"),
    ("J04.0", "Laringitis aguda", "X. Sistema respiratorio"),
    ("J05.0", "Laringitis obstructiva aguda (crup)", "X. Sistema respiratorio"),
    ("J06.9", "Infección aguda de las vías respiratorias superiores, no especificada", "X. Sistema respiratorio"),
    ("J11.1", "Influenza con otras manifestaciones respiratorias, virus no identificado", "X. Sistema respiratorio"),
    ("J11.8", "Influenza con otras manifestaciones, virus no identificado", "X. Sistema respiratorio"),
    ("J12.9", "Neumonía viral, no especificada", "X. Sistema respiratorio"),
    ("J15.9", "Neumonía bacteriana, no especificada", "X. Sistema respiratorio"),
    ("J18.0", "Bronconeumonía, no especificada", "X. Sistema respiratorio"),
    ("J18.9", "Neumonía, no especificada", "X. Sistema respiratorio"),
    ("J20.9", "Bronquitis aguda, no especificada", "X. Sistema respiratorio"),
    ("J21.9", "Bronquiolitis aguda, no especificada", "X. Sistema respiratorio"),
    ("J22.X", "Infección aguda no especificada de las vías respiratorias inferiores", "X. Sistema respiratorio"),
    ("J30.1", "Rinitis alérgica debida al polen", "X. Sistema respiratorio"),
    ("J30.4", "Rinitis alérgica, no especificada", "X. Sistema respiratorio"),
    ("J32.9", "Sinusitis crónica, no especificada", "X. Sistema respiratorio"),
    ("J35.0", "Amigdalitis crónica", "X. Sistema respiratorio"),
    ("J40.X", "Bronquitis, no especificada como aguda o crónica", "X. Sistema respiratorio"),
    ("J42.X", "Bronquitis crónica no especificada", "X. Sistema respiratorio"),
    ("J44.9", "Enfermedad pulmonar obstructiva crónica, no especificada", "X. Sistema respiratorio"),
    ("J45.0", "Asma predominantemente alérgica", "X. Sistema respiratorio"),
    ("J45.9", "Asma, no especificada", "X. Sistema respiratorio"),
    ("J46.X", "Estado asmático", "X. Sistema respiratorio"),
    ("J81.X", "Edema pulmonar", "X. Sistema respiratorio"),
    ("J90.X", "Derrame pleural no clasificado en otra parte", "X. Sistema respiratorio"),
    ("J96.0", "Insuficiencia respiratoria aguda", "X. Sistema respiratorio"),
    ("J98.4", "Otros trastornos del pulmón", "X. Sistema respiratorio"),

    # === CAP XI — K00-K93: Sistema digestivo ===
    ("K02.9", "Caries dental, no especificada", "XI. Sistema digestivo"),
    ("K05.1", "Gingivitis crónica", "XI. Sistema digestivo"),
    ("K05.3", "Periodontitis crónica", "XI. Sistema digestivo"),
    ("K08.1", "Pérdida de dientes debida a accidente, extracción o enfermedad periodontal local", "XI. Sistema digestivo"),
    ("K12.0", "Estomatitis aftosa recurrente", "XI. Sistema digestivo"),
    ("K21.0", "Enfermedad del reflujo gastroesofágico con esofagitis", "XI. Sistema digestivo"),
    ("K21.9", "Enfermedad del reflujo gastroesofágico sin esofagitis", "XI. Sistema digestivo"),
    ("K25.9", "Úlcera gástrica, no especificada como aguda o crónica, sin hemorragia ni perforación", "XI. Sistema digestivo"),
    ("K27.9", "Úlcera péptica, sitio no especificado", "XI. Sistema digestivo"),
    ("K29.0", "Gastritis aguda hemorrágica", "XI. Sistema digestivo"),
    ("K29.7", "Gastritis, no especificada", "XI. Sistema digestivo"),
    ("K30.X", "Dispepsia", "XI. Sistema digestivo"),
    ("K35.9", "Apendicitis aguda, no especificada", "XI. Sistema digestivo"),
    ("K40.9", "Hernia inguinal unilateral o no especificada, sin obstrucción ni gangrena", "XI. Sistema digestivo"),
    ("K42.9", "Hernia umbilical sin obstrucción ni gangrena", "XI. Sistema digestivo"),
    ("K52.9", "Colitis y gastroenteritis no infecciosas, no especificadas", "XI. Sistema digestivo"),
    ("K57.3", "Enfermedad diverticular del intestino grueso sin perforación ni absceso", "XI. Sistema digestivo"),
    ("K58.9", "Síndrome del colon irritable sin diarrea", "XI. Sistema digestivo"),
    ("K59.0", "Constipación", "XI. Sistema digestivo"),
    ("K60.0", "Fisura anal aguda", "XI. Sistema digestivo"),
    ("K64.9", "Hemorroides y trombosis hemorroidal perianal, no especificadas", "XI. Sistema digestivo"),
    ("K70.3", "Cirrosis hepática alcohólica", "XI. Sistema digestivo"),
    ("K70.9", "Enfermedad hepática alcohólica, no especificada", "XI. Sistema digestivo"),
    ("K76.0", "Degeneración grasa del hígado, no clasificada en otra parte", "XI. Sistema digestivo"),
    ("K80.2", "Cálculo de la vesícula biliar sin colecistitis", "XI. Sistema digestivo"),
    ("K81.0", "Colecistitis aguda", "XI. Sistema digestivo"),
    ("K81.9", "Colecistitis, no especificada", "XI. Sistema digestivo"),
    ("K85.9", "Pancreatitis aguda, no especificada", "XI. Sistema digestivo"),
    ("K92.0", "Hematemesis", "XI. Sistema digestivo"),
    ("K92.1", "Melena", "XI. Sistema digestivo"),

    # === CAP XII — L00-L99: Piel y tejido subcutáneo ===
    ("L01.0", "Impétigo", "XII. Piel y tejido subcutáneo"),
    ("L02.0", "Absceso cutáneo, furúnculo y carbunco de la cara", "XII. Piel y tejido subcutáneo"),
    ("L02.4", "Absceso cutáneo, furúnculo y carbunco de miembro", "XII. Piel y tejido subcutáneo"),
    ("L03.0", "Celulitis del dedo de la mano y del pie", "XII. Piel y tejido subcutáneo"),
    ("L03.9", "Celulitis, no especificada", "XII. Piel y tejido subcutáneo"),
    ("L20.9", "Dermatitis atópica, no especificada", "XII. Piel y tejido subcutáneo"),
    ("L21.9", "Dermatitis seborreica, no especificada", "XII. Piel y tejido subcutáneo"),
    ("L23.9", "Dermatitis alérgica de contacto, sin otra especificación", "XII. Piel y tejido subcutáneo"),
    ("L24.9", "Dermatitis de contacto por irritantes, sin otra especificación", "XII. Piel y tejido subcutáneo"),
    ("L25.9", "Dermatitis de contacto, no especificada, sin otra especificación", "XII. Piel y tejido subcutáneo"),
    ("L29.9", "Prurito, no especificado", "XII. Piel y tejido subcutáneo"),
    ("L40.9", "Psoriasis, no especificada", "XII. Piel y tejido subcutáneo"),
    ("L50.9", "Urticaria, no especificada", "XII. Piel y tejido subcutáneo"),
    ("L70.0", "Acné vulgar", "XII. Piel y tejido subcutáneo"),
    ("L70.9", "Acné, no especificado", "XII. Piel y tejido subcutáneo"),
    ("L72.0", "Quiste epidérmico", "XII. Piel y tejido subcutáneo"),
    ("L73.9", "Trastorno del folículo piloso, no especificado", "XII. Piel y tejido subcutáneo"),
    ("L81.0", "Hiperpigmentación postinflamatoria", "XII. Piel y tejido subcutáneo"),
    ("L98.9", "Trastorno de la piel y del tejido subcutáneo, no especificado", "XII. Piel y tejido subcutáneo"),

    # === CAP XIII — M00-M99: Sistema osteomuscular ===
    ("M05.9", "Artritis reumatoide seropositiva, no especificada", "XIII. Sistema osteomuscular"),
    ("M06.9", "Artritis reumatoide, no especificada", "XIII. Sistema osteomuscular"),
    ("M10.9", "Gota, no especificada", "XIII. Sistema osteomuscular"),
    ("M15.0", "Artrosis primaria generalizada", "XIII. Sistema osteomuscular"),
    ("M17.9", "Gonartrosis, no especificada", "XIII. Sistema osteomuscular"),
    ("M19.9", "Artrosis, no especificada", "XIII. Sistema osteomuscular"),
    ("M25.5", "Dolor articular", "XIII. Sistema osteomuscular"),
    ("M32.9", "Lupus eritematoso sistémico, no especificado", "XIII. Sistema osteomuscular"),
    ("M40.0", "Cifosis postural", "XIII. Sistema osteomuscular"),
    ("M41.9", "Escoliosis, no especificada", "XIII. Sistema osteomuscular"),
    ("M47.9", "Espondilosis, no especificada", "XIII. Sistema osteomuscular"),
    ("M51.1", "Trastornos de disco lumbar y otros, con radiculopatía", "XIII. Sistema osteomuscular"),
    ("M53.1", "Síndrome cervicobraquial", "XIII. Sistema osteomuscular"),
    ("M54.2", "Cervicalgia", "XIII. Sistema osteomuscular"),
    ("M54.4", "Lumbago con ciática", "XIII. Sistema osteomuscular"),
    ("M54.5", "Lumbago no especificado", "XIII. Sistema osteomuscular"),
    ("M54.9", "Dorsalgia, no especificada", "XIII. Sistema osteomuscular"),
    ("M62.6", "Distensión muscular", "XIII. Sistema osteomuscular"),
    ("M65.9", "Sinovitis y tenosinovitis, no especificada", "XIII. Sistema osteomuscular"),
    ("M75.0", "Capsulitis adhesiva del hombro", "XIII. Sistema osteomuscular"),
    ("M75.1", "Síndrome del manguito rotador", "XIII. Sistema osteomuscular"),
    ("M77.0", "Epicondilitis medial", "XIII. Sistema osteomuscular"),
    ("M77.1", "Epicondilitis lateral", "XIII. Sistema osteomuscular"),
    ("M79.1", "Mialgia", "XIII. Sistema osteomuscular"),
    ("M79.6", "Dolor en miembro", "XIII. Sistema osteomuscular"),
    ("M80.9", "Osteoporosis no especificada con fractura patológica", "XIII. Sistema osteomuscular"),
    ("M81.9", "Osteoporosis, no especificada", "XIII. Sistema osteomuscular"),

    # === CAP XIV — N00-N99: Sistema genitourinario ===
    ("N10.X", "Nefritis tubulointersticial aguda", "XIV. Sistema genitourinario"),
    ("N18.9", "Insuficiencia renal crónica, no especificada", "XIV. Sistema genitourinario"),
    ("N19.X", "Insuficiencia renal no especificada", "XIV. Sistema genitourinario"),
    ("N20.0", "Cálculo del riñón", "XIV. Sistema genitourinario"),
    ("N20.1", "Cálculo del uréter", "XIV. Sistema genitourinario"),
    ("N20.9", "Cálculo urinario, no especificado", "XIV. Sistema genitourinario"),
    ("N30.0", "Cistitis aguda", "XIV. Sistema genitourinario"),
    ("N30.9", "Cistitis, no especificada", "XIV. Sistema genitourinario"),
    ("N39.0", "Infección de vías urinarias, sitio no especificado", "XIV. Sistema genitourinario"),
    ("N40.X", "Hiperplasia de la próstata", "XIV. Sistema genitourinario"),
    ("N41.0", "Prostatitis aguda", "XIV. Sistema genitourinario"),
    ("N45.9", "Orquitis y epididimitis, no especificadas", "XIV. Sistema genitourinario"),
    ("N48.4", "Impotencia de origen orgánico", "XIV. Sistema genitourinario"),
    ("N60.1", "Mastopatía quística difusa", "XIV. Sistema genitourinario"),
    ("N61.X", "Trastornos inflamatorios de la mama", "XIV. Sistema genitourinario"),
    ("N76.0", "Vaginitis aguda", "XIV. Sistema genitourinario"),
    ("N76.1", "Vaginitis subaguda y crónica", "XIV. Sistema genitourinario"),
    ("N81.2", "Prolapso uterovaginal incompleto", "XIV. Sistema genitourinario"),
    ("N91.0", "Amenorrea primaria", "XIV. Sistema genitourinario"),
    ("N91.2", "Amenorrea, no especificada", "XIV. Sistema genitourinario"),
    ("N92.0", "Menstruación excesiva y frecuente con ciclo regular", "XIV. Sistema genitourinario"),
    ("N92.1", "Menstruación excesiva y frecuente con ciclo irregular", "XIV. Sistema genitourinario"),
    ("N94.6", "Dismenorrea, no especificada", "XIV. Sistema genitourinario"),
    ("N95.0", "Hemorragia postmenopáusica", "XIV. Sistema genitourinario"),
    ("N95.1", "Estados menopáusicos y climatéricos femeninos", "XIV. Sistema genitourinario"),

    # === CAP XV — O00-O99: Embarazo, parto y puerperio ===
    ("O02.1", "Aborto retenido", "XV. Embarazo, parto y puerperio"),
    ("O03.9", "Aborto espontáneo, completo o no especificado, sin complicación", "XV. Embarazo, parto y puerperio"),
    ("O10.0", "Hipertensión esencial preexistente que complica el embarazo, parto y puerperio", "XV. Embarazo, parto y puerperio"),
    ("O14.9", "Preeclampsia, no especificada", "XV. Embarazo, parto y puerperio"),
    ("O20.0", "Amenaza de aborto", "XV. Embarazo, parto y puerperio"),
    ("O21.0", "Hiperémesis gravídica leve", "XV. Embarazo, parto y puerperio"),
    ("O24.4", "Diabetes mellitus que se origina con el embarazo", "XV. Embarazo, parto y puerperio"),
    ("O60.1", "Trabajo de parto prematuro con parto prematuro", "XV. Embarazo, parto y puerperio"),
    ("O80.0", "Parto único espontáneo, presentación cefálica de vértice", "XV. Embarazo, parto y puerperio"),
    ("O82.9", "Parto único por cesárea, sin otra especificación", "XV. Embarazo, parto y puerperio"),
    ("Z34.0", "Supervisión de primer embarazo normal", "XV. Embarazo, parto y puerperio"),
    ("Z34.9", "Supervisión de embarazo normal, no especificado", "XV. Embarazo, parto y puerperio"),

    # === CAP XVI — P00-P96: Perinatal ===
    ("P07.1", "Otros recién nacidos de bajo peso", "XVI. Perinatal"),
    ("P59.9", "Ictericia neonatal, no especificada", "XVI. Perinatal"),

    # === CAP XVII — Q00-Q99: Malformaciones congénitas ===
    ("Q21.0", "Defecto del tabique ventricular", "XVII. Malformaciones congénitas"),
    ("Q21.1", "Defecto del tabique auricular", "XVII. Malformaciones congénitas"),
    ("Q90.9", "Síndrome de Down, no especificado", "XVII. Malformaciones congénitas"),

    # === CAP XVIII — R00-R99: Síntomas y hallazgos anormales ===
    ("R00.0", "Taquicardia, no especificada", "XVIII. Síntomas y hallazgos anormales"),
    ("R00.1", "Bradicardia, no especificada", "XVIII. Síntomas y hallazgos anormales"),
    ("R05.X", "Tos", "XVIII. Síntomas y hallazgos anormales"),
    ("R06.0", "Disnea", "XVIII. Síntomas y hallazgos anormales"),
    ("R06.2", "Sibilancias", "XVIII. Síntomas y hallazgos anormales"),
    ("R07.4", "Dolor en el pecho, no especificado", "XVIII. Síntomas y hallazgos anormales"),
    ("R10.0", "Abdomen agudo", "XVIII. Síntomas y hallazgos anormales"),
    ("R10.1", "Dolor localizado en parte superior del abdomen", "XVIII. Síntomas y hallazgos anormales"),
    ("R10.3", "Dolor localizado en otras partes del abdomen inferior", "XVIII. Síntomas y hallazgos anormales"),
    ("R10.4", "Otros dolores abdominales y los no especificados", "XVIII. Síntomas y hallazgos anormales"),
    ("R11.X", "Náusea y vómito", "XVIII. Síntomas y hallazgos anormales"),
    ("R14.X", "Flatulencia y afecciones afines", "XVIII. Síntomas y hallazgos anormales"),
    ("R17.X", "Ictericia no especificada", "XVIII. Síntomas y hallazgos anormales"),
    ("R19.7", "Diarrea, no especificada", "XVIII. Síntomas y hallazgos anormales"),
    ("R21.X", "Salpullido y otras erupciones cutáneas no especificadas", "XVIII. Síntomas y hallazgos anormales"),
    ("R30.0", "Disuria", "XVIII. Síntomas y hallazgos anormales"),
    ("R31.X", "Hematuria, no especificada", "XVIII. Síntomas y hallazgos anormales"),
    ("R33.X", "Retención de orina", "XVIII. Síntomas y hallazgos anormales"),
    ("R35.X", "Poliuria", "XVIII. Síntomas y hallazgos anormales"),
    ("R40.0", "Somnolencia", "XVIII. Síntomas y hallazgos anormales"),
    ("R42.X", "Mareo y desvanecimiento", "XVIII. Síntomas y hallazgos anormales"),
    ("R50.9", "Fiebre, no especificada", "XVIII. Síntomas y hallazgos anormales"),
    ("R51.X", "Cefalea", "XVIII. Síntomas y hallazgos anormales"),
    ("R52.0", "Dolor agudo", "XVIII. Síntomas y hallazgos anormales"),
    ("R52.2", "Otro dolor crónico", "XVIII. Síntomas y hallazgos anormales"),
    ("R53.X", "Malestar y fatiga", "XVIII. Síntomas y hallazgos anormales"),
    ("R55.X", "Síncope y colapso", "XVIII. Síntomas y hallazgos anormales"),
    ("R56.0", "Convulsiones febriles", "XVIII. Síntomas y hallazgos anormales"),
    ("R56.8", "Convulsiones, no clasificadas en otra parte", "XVIII. Síntomas y hallazgos anormales"),
    ("R60.0", "Edema localizado", "XVIII. Síntomas y hallazgos anormales"),
    ("R63.0", "Anorexia", "XVIII. Síntomas y hallazgos anormales"),
    ("R63.4", "Pérdida anormal de peso", "XVIII. Síntomas y hallazgos anormales"),
    ("R73.9", "Hiperglicemia, no especificada", "XVIII. Síntomas y hallazgos anormales"),

    # === CAP XIX — S00-T98: Traumatismos y envenenamientos ===
    ("S00.0", "Traumatismo superficial del cuero cabelludo", "XIX. Traumatismos y envenenamientos"),
    ("S01.0", "Herida del cuero cabelludo", "XIX. Traumatismos y envenenamientos"),
    ("S06.0", "Concusión", "XIX. Traumatismos y envenenamientos"),
    ("S06.9", "Traumatismo intracraneal, no especificado", "XIX. Traumatismos y envenenamientos"),
    ("S13.4", "Esguince y torcedura de la columna cervical", "XIX. Traumatismos y envenenamientos"),
    ("S20.2", "Contusión del tórax", "XIX. Traumatismos y envenenamientos"),
    ("S22.3", "Fractura de costilla", "XIX. Traumatismos y envenenamientos"),
    ("S32.0", "Fractura de vértebra lumbar", "XIX. Traumatismos y envenenamientos"),
    ("S42.0", "Fractura de la clavícula", "XIX. Traumatismos y envenenamientos"),
    ("S42.2", "Fractura del húmero, parte superior", "XIX. Traumatismos y envenenamientos"),
    ("S52.5", "Fractura del extremo distal del radio", "XIX. Traumatismos y envenenamientos"),
    ("S60.0", "Contusión de dedo(s) de la mano sin daño de la(s) uña(s)", "XIX. Traumatismos y envenenamientos"),
    ("S62.6", "Fractura de otro dedo de la mano", "XIX. Traumatismos y envenenamientos"),
    ("S72.0", "Fractura del cuello del fémur", "XIX. Traumatismos y envenenamientos"),
    ("S73.0", "Luxación de la cadera", "XIX. Traumatismos y envenenamientos"),
    ("S82.6", "Fractura del maléolo lateral", "XIX. Traumatismos y envenenamientos"),
    ("S83.5", "Esguince y torcedura que comprometen el ligamento cruzado de la rodilla", "XIX. Traumatismos y envenenamientos"),
    ("S86.0", "Traumatismo del tendón calcáneo", "XIX. Traumatismos y envenenamientos"),
    ("S93.4", "Esguince y torcedura de tobillo", "XIX. Traumatismos y envenenamientos"),
    ("T14.0", "Traumatismo superficial de región no especificada del cuerpo", "XIX. Traumatismos y envenenamientos"),
    ("T14.9", "Traumatismo, no especificado", "XIX. Traumatismos y envenenamientos"),
    ("T30.0", "Quemadura de región corporal no especificada, grado no especificado", "XIX. Traumatismos y envenenamientos"),
    ("T78.0", "Choque anafiláctico debido a reacción adversa a alimentos", "XIX. Traumatismos y envenenamientos"),
    ("T78.4", "Alergia, no especificada", "XIX. Traumatismos y envenenamientos"),
    ("T88.7", "Efecto adverso no especificado por droga o medicamento", "XIX. Traumatismos y envenenamientos"),

    # === CAP XXI — Z00-Z99: Factores que influyen en el estado de salud ===
    ("Z00.0", "Examen médico general", "XXI. Factores que influyen en el estado de salud"),
    ("Z00.1", "Control de salud de rutina del niño", "XXI. Factores que influyen en el estado de salud"),
    ("Z01.4", "Examen ginecológico (general) (de rutina)", "XXI. Factores que influyen en el estado de salud"),
    ("Z02.0", "Examen para la admisión a instituciones educativas", "XXI. Factores que influyen en el estado de salud"),
    ("Z02.1", "Examen pre-empleo", "XXI. Factores que influyen en el estado de salud"),
    ("Z02.5", "Examen para fines deportivos", "XXI. Factores que influyen en el estado de salud"),
    ("Z02.9", "Examen para fines administrativos, no especificado", "XXI. Factores que influyen en el estado de salud"),
    ("Z03.9", "Observación por sospecha de enfermedad o afección no especificada", "XXI. Factores que influyen en el estado de salud"),
    ("Z23.X", "Necesidad de inmunización contra una sola enfermedad bacteriana", "XXI. Factores que influyen en el estado de salud"),
    ("Z25.1", "Necesidad de inmunización contra la influenza", "XXI. Factores que influyen en el estado de salud"),
    ("Z30.0", "Consejo y asesoramiento general sobre la anticoncepción", "XXI. Factores que influyen en el estado de salud"),
    ("Z30.4", "Supervisión del uso de drogas anticonceptivas", "XXI. Factores que influyen en el estado de salud"),
    ("Z32.0", "Embarazo (aún) no confirmado", "XXI. Factores que influyen en el estado de salud"),
    ("Z33.X", "Estado de embarazo, incidental", "XXI. Factores que influyen en el estado de salud"),
    ("Z39.2", "Atención y examen postparto de rutina", "XXI. Factores que influyen en el estado de salud"),
    ("Z71.3", "Asesoramiento y vigilancia dietética", "XXI. Factores que influyen en el estado de salud"),
    ("Z76.0", "Repetición de receta", "XXI. Factores que influyen en el estado de salud"),
]


class Command(BaseCommand):
    help = "Carga el catálogo CIE-10 (Clasificación Internacional de Enfermedades) en español."

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            help='Ruta opcional a CSV con codigo,descripcion,capitulo para cargar códigos adicionales.',
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Borra el catálogo existente antes de cargar.',
        )

    def handle(self, *args, **options):
        if options['limpiar']:
            count = CodigoCIE10.objects.count()
            CodigoCIE10.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Borrados {count} códigos CIE-10 existentes."))

        # Carga set base embebido
        creados, actualizados = self._cargar_lista(CIE10_BASE)
        self.stdout.write(self.style.SUCCESS(
            f"Set base CIE-10: {creados} creados, {actualizados} actualizados."
        ))

        # Carga CSV adicional si se especifica
        if options['csv']:
            ruta = Path(options['csv'])
            if not ruta.exists():
                self.stdout.write(self.style.ERROR(f"CSV no encontrado: {ruta}"))
                return
            extra = self._leer_csv(ruta)
            ext_c, ext_a = self._cargar_lista(extra)
            self.stdout.write(self.style.SUCCESS(
                f"CSV adicional: {ext_c} creados, {ext_a} actualizados."
            ))

        total = CodigoCIE10.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"\nTotal códigos CIE-10 en catálogo: {total}"
        ))

    @transaction.atomic
    def _cargar_lista(self, lista):
        creados = 0
        actualizados = 0
        for codigo, descripcion, capitulo in lista:
            obj, created = CodigoCIE10.objects.update_or_create(
                codigo=codigo,
                defaults={'descripcion': descripcion, 'capitulo': capitulo},
            )
            if created:
                creados += 1
            else:
                actualizados += 1
        return creados, actualizados

    def _leer_csv(self, ruta):
        items = []
        with open(ruta, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                codigo = (row.get('codigo') or '').strip()
                descripcion = (row.get('descripcion') or '').strip()
                capitulo = (row.get('capitulo') or '').strip()
                if codigo and descripcion:
                    items.append((codigo, descripcion, capitulo))
        return items
