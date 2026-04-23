from django.urls import path
from .api_views import (
    EmitirFacturaView,
    ListarFacturasView,
    DetalleFacturaView,
    ReenviarFacturaView,
    ConsultarAutorizacionView,
)

urlpatterns = [
    path('emitir/', EmitirFacturaView.as_view(), name='api_emitir_factura'),
    path('', ListarFacturasView.as_view(), name='api_lista_facturas'),
    path('<int:factura_id>/', DetalleFacturaView.as_view(), name='api_detalle_factura'),
    path('<int:factura_id>/reenviar/', ReenviarFacturaView.as_view(), name='api_reenviar_factura'),
    path('<int:factura_id>/consultar/', ConsultarAutorizacionView.as_view(), name='api_consultar_autorizacion'),
]
