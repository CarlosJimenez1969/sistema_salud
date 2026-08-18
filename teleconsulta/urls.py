from django.urls import path

from . import views

app_name = 'teleconsulta'

urlpatterns = [
    # Médico (con login)
    path('cita/<int:cita_id>/abrir/', views.abrir_sala_cita, name='abrir_sala_cita'),
    path('sala/<int:sesion_id>/', views.sala_medico, name='sala_medico'),
    path('sala/<int:sesion_id>/admitir/', views.admitir, name='admitir'),
    path('sala/<int:sesion_id>/finalizar/', views.finalizar, name='finalizar'),
    path('sala/<int:sesion_id>/estado/', views.estado_medico_json, name='estado_medico'),

    # Paciente (por token, sin login)
    path('t/<str:token>/', views.entrada, name='entrada'),
    path('t/<str:token>/consentimiento/', views.consentimiento, name='consentimiento'),
    path('t/<str:token>/precheck/', views.precheck, name='precheck'),
    path('t/<str:token>/listo/', views.listo, name='listo'),
    path('t/<str:token>/espera/', views.sala_espera, name='sala_espera'),
    path('t/<str:token>/video/', views.sala_paciente, name='sala_paciente'),
    path('t/<str:token>/estado/', views.estado_json, name='estado'),
]
