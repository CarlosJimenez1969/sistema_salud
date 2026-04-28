from django.db import migrations

DATOS = {
    'Ecuador':    ['Quito', 'Guayaquil', 'Cuenca', 'Ambato', 'Loja', 'Ibarra', 'Riobamba', 'Machala', 'Portoviejo', 'Manta', 'Esmeraldas', 'Santo Domingo'],
    'Colombia':   ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena', 'Cúcuta', 'Bucaramanga', 'Pereira', 'Manizales', 'Santa Marta'],
    'Perú':       ['Lima', 'Arequipa', 'Trujillo', 'Chiclayo', 'Piura', 'Iquitos', 'Cusco', 'Huancayo', 'Tacna', 'Pucallpa'],
    'Bolivia':    ['La Paz', 'Santa Cruz de la Sierra', 'Cochabamba', 'Oruro', 'Potosí', 'Sucre', 'Tarija', 'Trinidad'],
    'Chile':      ['Santiago', 'Valparaíso', 'Concepción', 'Antofagasta', 'Temuco', 'Rancagua', 'Talca', 'Iquique', 'Arica'],
    'Argentina':  ['Buenos Aires', 'Córdoba', 'Rosario', 'Mendoza', 'La Plata', 'Tucumán', 'Mar del Plata', 'Salta', 'Santa Fe'],
    'Venezuela':  ['Caracas', 'Maracaibo', 'Valencia', 'Barquisimeto', 'Maracay', 'Ciudad Guayana', 'Mérida', 'Maturín'],
    'Paraguay':   ['Asunción', 'Ciudad del Este', 'San Lorenzo', 'Luque', 'Capiatá', 'Lambaré', 'Fernando de la Mora'],
    'Uruguay':    ['Montevideo', 'Salto', 'Ciudad de la Costa', 'Paysandú', 'Las Piedras', 'Rivera', 'Maldonado'],
    'Brasil':     ['São Paulo', 'Río de Janeiro', 'Brasília', 'Salvador', 'Fortaleza', 'Belo Horizonte', 'Manaus', 'Curitiba', 'Recife', 'Porto Alegre'],
    'Guyana':     ['Georgetown', 'Linden', 'New Amsterdam'],
    'Surinam':    ['Paramaribo', 'Lelydorp', 'Nieuw Nickerie'],
}


def cargar_datos(apps, schema_editor):
    Pais = apps.get_model('medico', 'Pais')
    Ciudad = apps.get_model('medico', 'Ciudad')
    for nombre_pais, ciudades in DATOS.items():
        pais, _ = Pais.objects.get_or_create(nombre=nombre_pais)
        for nombre_ciudad in ciudades:
            Ciudad.objects.get_or_create(nombre=nombre_ciudad, pais=pais)


def revertir(apps, schema_editor):
    apps.get_model('medico', 'Ciudad').objects.all().delete()
    apps.get_model('medico', 'Pais').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('medico', '0006_add_pais_ciudad'),
    ]
    operations = [
        migrations.RunPython(cargar_datos, revertir),
    ]
