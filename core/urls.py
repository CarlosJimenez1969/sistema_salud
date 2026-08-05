from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# Importamos las vistas
from users.views import home, registro_medico, pasarela_pago, pago_exitoso, registro_exitoso, panel_admin, contacto, renovar_suscripcion, confirmar_renovacion, cron_notificar_suscripciones, cron_limpiar_datos_prueba
from medico.views import configurar_horario, ciudades_por_pais
from paciente.views import (
    listar_pacientes, crear_paciente, editar_paciente, registro_paciente,
    listar_mascotas, crear_mascota, editar_mascota, eliminar_mascota,
    crear_paciente_veterinario, buscar_pacientes_ajax, buscar_por_cedula,
)
from historia.views import crear_historia, historial_medico, imprimir_receta, registrar_triaje, buscar_cie10  # <--- IMPORTANTE: Importar historial_medico
from citas.views import buscar_medico, reservar_cita, ver_agenda
from medico.ficha_views import (
    ficha_publica, FichaEditView, ficha_qr, solicitudes_cita, cambiar_estado_solicitud,
)

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

    # Mascotas
    path('mascotas/',                       listar_mascotas,  name='listar_mascotas'),
    path('mascotas/nueva/',                 crear_mascota,    name='crear_mascota'),
    path('mascotas/editar/<int:mascota_id>/', editar_mascota, name='editar_mascota'),
    path('mascotas/eliminar/<int:mascota_id>/', eliminar_mascota, name='eliminar_mascota'),
    path('api/buscar-pacientes/', buscar_pacientes_ajax, name='buscar_pacientes_ajax'),
    path('api/buscar-por-cedula/<str:cedula>/', buscar_por_cedula, name='buscar_por_cedula'),

    # Pacientes
    path('pacientes/', listar_pacientes, name='listar_pacientes'),
    path('pacientes/nuevo/', crear_paciente, name='crear_paciente'),
    path('pacientes/nuevo/veterinario/', crear_paciente_veterinario, name='crear_paciente_veterinario'),
    path('pacientes/editar/<int:id>/', editar_paciente, name='editar_paciente'),

    # Historias Clínicas
    path('historia/crear/<int:paciente_id>/', crear_historia, name='crear_historia'),
    path('historia/paciente/<int:paciente_id>/', historial_medico, name='historial_medico'),
    path('historia/receta/<int:historia_id>/', imprimir_receta, name='imprimir_receta'),
    path('historia/triaje/<int:cita_id>/', registrar_triaje, name='registrar_triaje'),
    path('api/buscar-cie10/', buscar_cie10, name='buscar_cie10'),

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
    path('contacto/', contacto, name='contacto'),
    path('renovar-suscripcion/', renovar_suscripcion, name='renovar_suscripcion'),
    path('confirmar-renovacion/', confirmar_renovacion, name='confirmar_renovacion'),
    path('cron/notificar/', cron_notificar_suscripciones, name='cron_notificar_suscripciones'),
    path('cron/limpiar/', cron_limpiar_datos_prueba, name='cron_limpiar_datos_prueba'),
    path('configurar-horario/', configurar_horario, name='configurar_horario'),
    path('api/ciudades/', ciudades_por_pais, name='ciudades_por_pais'),
    path('login-success/', views.redirect_by_role, name='login_success'),
    path('citas/resumen/<int:paciente_id>/', paciente_views.resumen_paciente_rapido, name='resumen_paciente'),

    path('pago-exitoso/', pago_exitoso, name='pago_exitoso'),
    path('registro-exitoso/', registro_exitoso, name='registro_exitoso'),

    path('confirmar-pago/', users_views.confirmar_pago, name='confirmar_pago'),
    path('pasarela-pago/', users_views.pasarela_pago, name='pasarela_pago'),

    # Ficha pública del médico (SEO) + solicitudes de cita
    path('mi-ficha/', FichaEditView.as_view(), name='ficha_editar'),
    path('mi-ficha/qr/', ficha_qr, name='ficha_qr'),
    path('solicitudes-cita/', solicitudes_cita, name='solicitudes_cita'),
    path('solicitudes-cita/<int:sol_id>/<str:accion>/', cambiar_estado_solicitud, name='cambiar_estado_solicitud'),

    # Página pública (sin login) — al final para no capturar otras rutas
    path('p/<slug:slug>/', ficha_publica, name='ficha_publica'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)