from os import path

from citas import views

urlpatterns = [
    path('crear/<int:paciente_id>/', views.crear_historia, name='crear_historia'),
    path('obtener_signos/<int:paciente_id>/', views.obtener_ultimos_signos, name='obtener_signos'),
    path('triaje/<int:cita_id>/', views.registrar_triaje, name='registrar_triaje'),
]
