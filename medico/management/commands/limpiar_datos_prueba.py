"""
Limpia la base de datos para empezar pruebas desde cero.

PRESERVA:
- Usuario ADMIN (superuser)
- Especialidades médicas
- Países y Ciudades

ELIMINA:
- Todos los demás usuarios (médicos, secretarias, pacientes)
- Médicos, Secretarias, Pacientes, Mascotas
- Citas, Historias clínicas, imágenes, recetas
- Facturas electrónicas
- Registros pendientes de pago

Uso:
    python manage.py limpiar_datos_prueba
    python manage.py limpiar_datos_prueba --confirmar
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


class Command(BaseCommand):
    help = 'Limpia datos de prueba pero mantiene admin, especialidades y ubicaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirmación para ejecutar la limpieza realmente',
        )

    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(self.style.WARNING(
                "MODO SIMULACIÓN. Para ejecutar realmente, agrega --confirmar\n"
                "Ejemplo: python manage.py limpiar_datos_prueba --confirmar\n"
            ))

        User = get_user_model()
        from medico.models import Medico, Secretaria
        from paciente.models import Paciente, Mascota
        from citas.models import Cita
        from historia.models import HistoriaClinica
        from facturacion.models import FacturaElectronica
        from users.models import RegistroPendiente

        # Conteos antes
        self.stdout.write("\n--- ANTES DE LA LIMPIEZA ---")
        self.stdout.write(f"Usuarios totales: {User.objects.count()}")
        self.stdout.write(f"Médicos: {Medico.objects.count()}")
        self.stdout.write(f"Secretarias: {Secretaria.objects.count()}")
        self.stdout.write(f"Pacientes: {Paciente.objects.count()}")
        self.stdout.write(f"Mascotas: {Mascota.objects.count()}")
        self.stdout.write(f"Citas: {Cita.objects.count()}")
        self.stdout.write(f"Historias clínicas: {HistoriaClinica.objects.count()}")
        self.stdout.write(f"Facturas: {FacturaElectronica.objects.count()}")
        self.stdout.write(f"Registros pendientes: {RegistroPendiente.objects.count()}")

        # IDs de admins a preservar
        admin_ids = list(User.objects.filter(is_superuser=True).values_list('id', flat=True))
        self.stdout.write(f"\nUsuarios admin a preservar: {admin_ids}")

        if not options['confirmar']:
            self.stdout.write(self.style.WARNING("\n(Sin --confirmar, no se eliminó nada.)"))
            return

        with transaction.atomic():
            # 1. Eliminar facturas
            FacturaElectronica.objects.all().delete()
            # 2. Eliminar registros pendientes
            RegistroPendiente.objects.all().delete()
            # 3. Eliminar historias clínicas (cascade borra imágenes y especialidades)
            HistoriaClinica.objects.all().delete()
            # 4. Eliminar citas
            Cita.objects.all().delete()
            # 5. Eliminar mascotas
            Mascota.objects.all().delete()
            # 6. Eliminar pacientes (no admin)
            Paciente.objects.exclude(usuario_id__in=admin_ids).delete()
            # 7. Eliminar secretarias
            Secretaria.objects.all().delete()
            # 8. Eliminar médicos (no admin)
            Medico.objects.exclude(usuario_id__in=admin_ids).delete()
            # 9. Eliminar usuarios que NO son admin
            User.objects.exclude(id__in=admin_ids).delete()

        self.stdout.write(self.style.SUCCESS("\n--- DESPUÉS DE LA LIMPIEZA ---"))
        self.stdout.write(self.style.SUCCESS(f"Usuarios totales: {User.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Médicos: {Medico.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Pacientes: {Paciente.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Citas: {Cita.objects.count()}"))
        self.stdout.write(self.style.SUCCESS("\n✅ Limpieza completada. Especialidades, países y admin preservados."))
