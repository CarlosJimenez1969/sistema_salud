from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# Importamos las vistas
from users.views import home, registro_medico, pasarela_pago, pago_exitoso, crear_orden_paypal, registro_exitoso, panel_admin
from medico.views import configurar_horario
from paciente.views import listar_pacientes, crear_paciente, editar_paciente, registro_paciente
from historia.views import crear_historia, historial_medico, imprimir_receta, registrar_triaje  # <--- IMPORTANTE: Importar historial_medico
from citas.views import buscar_medico, reservar_cita, ver_agenda

from paciente import views as paciente_views

from users import views
from users import views as users_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('citas/', include('citas.urls')),
    path('facturas/', include('facturacion.urls')),
    path('api/v1/facturas/', include('facturacion.api_urls')),

    # Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', home, name='home'),

    # Registro de Médicos
    path('registro-medico/', users_views.registro_medico, name='registro_medico'),
    path('pago-suscripcion/', pasarela_pago, name='pasarela_pago'),

    # Registro secretaria
    path('crear-secretaria/', views.crear_secretaria, name='crear_secretaria'),
    path('eliminar-secretaria/<int:secretaria_id>/', views.eliminar_secretaria, name='eliminar_secretaria'),

    # Registro ciudadano / paciente
    path('registro-paciente/', registro_paciente, name='registro_paciente'),

    # Pacientes
    path('pacientes/', listar_pacientes, name='listar_pacientes'),
    path('pacientes/nuevo/', crear_paciente, name='crear_paciente'),
    path('pacientes/editar/<int:id>/', editar_paciente, name='editar_paciente'),

    # Historias Clínicas
    path('historia/crear/<int:paciente_id>/', crear_historia, name='crear_historia'),
    path('historia/paciente/<int:paciente_id>/', historial_medico, name='historial_medico'),
    path('historia/receta/<int:historia_id>/', imprimir_receta, name='imprimir_receta'),
    path('historia/triaje/<int:cita_id>/', registrar_triaje, name='registrar_triaje'),

    # Citas (rutas no incluidas en citas/urls.py)
    path('citas/buscar/', buscar_medico, name='buscar_medico'),
    path('citas/agenda/', ver_agenda, name='ver_agenda'),

    # Autenticación Django
    path('accounts/', include('django.contrib.auth.urls')),

    path('asignar-password/<int:user_id>/', views.asignar_password, name='asignar_password'),

    path('reset/<uidb64>/<token>/',
         views.ActivarCuentaConfirmView.as_view(),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),

    path('panel-admin/', panel_admin, name='panel_admin'),
    path('configurar-horario/', configurar_horario, name='configurar_horario'),
    path('login-success/', views.redirect_by_role, name='login_success'),
    path('citas/resumen/<int:paciente_id>/', paciente_views.resumen_paciente_rapido, name='resumen_paciente'),

    path('probar-email/', views.probar_email, name='probar_email'),
    path('pago-exitoso/', pago_exitoso, name='pago_exitoso'),
    path('registro-exitoso/', registro_exitoso, name='registro_exitoso'),
    path('crear-orden-paypal/', crear_orden_paypal, name='crear_orden_paypal'),
    path('confirmar-pago/', users_views.confirmar_pago, name='confirmar_pago'),
    path('pasarela-pago/', users_views.pasarela_pago, name='pasarela_pago'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)