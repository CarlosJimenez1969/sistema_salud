from django.db import migrations


def agregar_veterinaria(apps, schema_editor):
    Especialidad = apps.get_model('medico', 'Especialidad')
    Especialidad.objects.get_or_create(
        nombre='Veterinaria',
        defaults={'descripcion': 'Atención médica para mascotas y animales.'}
    )


def quitar_veterinaria(apps, schema_editor):
    Especialidad = apps.get_model('medico', 'Especialidad')
    Especialidad.objects.filter(nombre='Veterinaria').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('medico', '0007_datos_iniciales_paises_ciudades'),
    ]
    operations = [
        migrations.RunPython(agregar_veterinaria, quitar_veterinaria),
    ]
