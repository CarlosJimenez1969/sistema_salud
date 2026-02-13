from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# Importamos las vistas
from users.views import home, registro_medico, pasarela_pago
from paciente.views import listar_pacientes, crear_paciente, editar_paciente
from historia.views import crear_historia, historial_medico, imprimir_receta  # <--- IMPORTANTE: Importar historial_medico
from citas.views import buscar_medico, reservar_cita, ver_agenda

from users import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', home, name='home'),
    
    # Registro de Médicos
    path('registro-medico/', registro_medico, name='registro_medico'),
    path('crear-secretaria/', views.crear_secretaria, name='crear_secretaria'),
    path('pago-suscripcion/', pasarela_pago, name='pasarela_pago'),

    # Pacientes
    path('pacientes/', listar_pacientes, name='listar_pacientes'),
    path('pacientes/nuevo/', crear_paciente, name='crear_paciente'),
    path('pacientes/editar/<int:id>/', editar_paciente, name='editar_paciente'),

    # Historias Clínicas
    path('historia/crear/<int:paciente_id>/', crear_historia, name='crear_historia'),
    
    # ESTA ES LA LÍNEA QUE TE FALTA O TIENE ERROR:
    path('historia/paciente/<int:paciente_id>/', historial_medico, name='historial_medico'),
    path('historia/receta/<int:historia_id>/', imprimir_receta, name='imprimir_receta'),

    #citas
    path('citas/buscar/', buscar_medico, name='buscar_medico'),
    path('citas/reservar/<int:medico_id>/', reservar_cita, name='reservar_cita'),
    path('citas/agenda/', ver_agenda, name='ver_agenda'),

    # Esto habilita: login, logout, password_reset, password_reset_confirm, etc.
    path('accounts/', include('django.contrib.auth.urls')),

    # Tus otras rutas...
    #path('', include('medico.urls')), # o como se llame tu app
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)