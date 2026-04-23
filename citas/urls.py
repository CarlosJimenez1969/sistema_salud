from django.urls import path
from . import views

urlpatterns = [
    #path('dashboard/', views.dashboard_secretaria, name='dashboard_secretaria'),
    path('dashboard-secretaria/', views.dashboard_secretaria, name='dashboard_secretaria'),
    
    # Esta es la vista que ya tienes, ahora con el nombre que el Dashboard busca
    path('agendar/', views.buscar_medico, name='agendar_cita'), 
    
    # La vista que procesa el calendario del médico elegido
    path('reservar/<int:medico_id>/', views.reservar_cita, name='reservar_cita'),

    path('estado/<int:cita_id>/<str:nuevo_estado>/', views.cambiar_estado_cita, name='cambiar_estado_cita'),
    path('editar/<int:cita_id>/', views.editar_cita, name='editar_cita'),
    path('eliminar/<int:cita_id>/', views.eliminar_cita, name='eliminar_cita'),
]