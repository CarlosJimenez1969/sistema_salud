from django.db import migrations
from datetime import date, timedelta


def inicializar(apps, schema_editor):
    Medico = apps.get_model('medico', 'Medico')
    User = apps.get_model('users', 'User')
    hoy = date.today()
    for m in Medico.objects.all():
        # Si no tiene fechas, asignar 30 días desde hoy
        if not m.fecha_inicio_suscripcion:
            m.fecha_inicio_suscripcion = hoy
            # Médicos que ya pagaron (pago_realizado=True) reciben 1 año pagado
            try:
                if m.usuario.pago_realizado:
                    m.fecha_fin_suscripcion = hoy + timedelta(days=365)
                    m.en_periodo_prueba = False
                else:
                    m.fecha_fin_suscripcion = hoy + timedelta(days=30)
                    m.en_periodo_prueba = True
            except Exception:
                m.fecha_fin_suscripcion = hoy + timedelta(days=30)
                m.en_periodo_prueba = True
            m.save()


def revertir(apps, schema_editor):
    Medico = apps.get_model('medico', 'Medico')
    Medico.objects.update(
        fecha_inicio_suscripcion=None,
        fecha_fin_suscripcion=None,
        en_periodo_prueba=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('medico', '0009_add_suscripcion'),
    ]
    operations = [
        migrations.RunPython(inicializar, revertir),
    ]
