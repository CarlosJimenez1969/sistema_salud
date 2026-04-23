from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_facturas, name='lista_facturas'),
    path('<int:factura_id>/', views.detalle_factura, name='detalle_factura'),
    path('<int:factura_id>/reenviar/', views.reenviar_factura, name='reenviar_factura'),
    path('<int:factura_id>/consultar/', views.consultar_autorizacion, name='consultar_autorizacion_sri'),
]
