from django.db import migrations


CORRECCIONES = {
    'oftalmologia':        'Oftalmología',
    'Cardiologia':         'Cardiología',
    'Dermatologia':        'Dermatología',
    'Odontologia':         'Odontología',
    'Otorrinolaringologia':'Otorrinolaringología',
    'Nuitrición':          'Nutrición',
    'Traumatologia':       'Traumatología',
}

NUEVAS_ESPECIALIDADES = [
    'Neurología',
    'Endocrinología',
    'Medicina Interna',
    'Cirugía General',
    'Urología',
    'Neumología',
    'Nefrología',
    'Ortopedia',
    'Medicina de Emergencias',
]


def corregir_y_agregar(apps, schema_editor):
    Especialidad = apps.get_model('medico', 'Especialidad')

    for nombre_viejo, nombre_nuevo in CORRECCIONES.items():
        Especialidad.objects.filter(nombre=nombre_viejo).update(nombre=nombre_nuevo)

    existentes = set(Especialidad.objects.values_list('nombre', flat=True))
    for nombre in NUEVAS_ESPECIALIDADES:
        if nombre not in existentes:
            Especialidad.objects.create(nombre=nombre)


def revertir(apps, schema_editor):
    Especialidad = apps.get_model('medico', 'Especialidad')
    nombres_invertidos = {v: k for k, v in CORRECCIONES.items()}
    for nombre_nuevo, nombre_viejo in nombres_invertidos.items():
        Especialidad.objects.filter(nombre=nombre_nuevo).update(nombre=nombre_viejo)
    for nombre in NUEVAS_ESPECIALIDADES:
        Especialidad.objects.filter(nombre=nombre).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('medico', '0002_secretaria'),
    ]

    operations = [
        migrations.RunPython(corregir_y_agregar, revertir),
    ]
