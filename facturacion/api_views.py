from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import FacturaElectronica
from .api_serializers import EmitirFacturaSerializer, FacturaElectronicaSerializer


class EmitirFacturaView(APIView):
    """
    POST /api/v1/facturas/emitir/
    Genera, firma y envía una nueva factura electrónica al SRI.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EmitirFacturaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        receptor = data['receptor']
        items = data['items']
        forma_pago = data.get('forma_pago', '01')

        subtotal = sum(
            Decimal(str(i['cantidad'])) * Decimal(str(i['precio_unitario'])) - Decimal(str(i['descuento']))
            for i in items
        )

        from django.conf import settings
        iva_pct = Decimal(str(getattr(settings, 'SRI_IVA_PORCENTAJE', '0')))
        iva_valor = (subtotal * iva_pct / 100).quantize(Decimal('0.01'))
        total = subtotal + iva_valor

        descripcion = items[0]['descripcion'] if len(items) == 1 else f"{len(items)} servicios"

        from .services.sri import SriService
        from .models import SecuencialFactura

        establecimiento = getattr(settings, 'SRI_ESTABLECIMIENTO', '001')
        punto_emision = getattr(settings, 'SRI_PUNTO_EMISION', '001')
        secuencial = SecuencialFactura.siguiente(establecimiento, punto_emision)
        numero_secuencial = f"{establecimiento}-{punto_emision}-{secuencial:09d}"

        servicio = SriService()
        clave_acceso = servicio.generar_clave_acceso(
            fecha=timezone.now().date(),
            secuencial=secuencial,
        )

        factura = FacturaElectronica(
            clave_acceso=clave_acceso,
            numero_secuencial=numero_secuencial,
            secuencial_numero=secuencial,
            receptor_tipo_id=receptor['tipo_identificacion'],
            receptor_identificacion=receptor['identificacion'],
            receptor_nombre=receptor['nombre'],
            receptor_email=receptor.get('email', ''),
            receptor_direccion=receptor.get('direccion', 'N/A'),
            subtotal=subtotal,
            iva_porcentaje=iva_pct,
            iva_valor=iva_valor,
            total=total,
            descripcion=descripcion,
            estado='PENDIENTE',
        )
        factura.forma_pago = forma_pago
        factura._items_api = items

        try:
            servicio.procesar_factura(factura)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        out = FacturaElectronicaSerializer(factura)
        http_status = (
            status.HTTP_201_CREATED
            if factura.estado == 'AUTORIZADA'
            else status.HTTP_202_ACCEPTED
        )
        return Response(out.data, status=http_status)


class ListarFacturasView(APIView):
    """
    GET /api/v1/facturas/
    Lista facturas con filtros opcionales: q, estado, fecha_desde, fecha_hasta.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = FacturaElectronica.objects.all().order_by('-fecha_emision')

        q = request.query_params.get('q', '').strip()
        estado = request.query_params.get('estado', '').strip()
        fecha_desde = request.query_params.get('fecha_desde', '').strip()
        fecha_hasta = request.query_params.get('fecha_hasta', '').strip()

        if q:
            qs = qs.filter(receptor_nombre__icontains=q) | \
                 qs.filter(receptor_identificacion__icontains=q) | \
                 qs.filter(numero_secuencial__icontains=q)
        if estado:
            qs = qs.filter(estado=estado.upper())
        if fecha_desde:
            qs = qs.filter(fecha_emision__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_emision__date__lte=fecha_hasta)

        serializer = FacturaElectronicaSerializer(qs, many=True)
        return Response({'count': qs.count(), 'results': serializer.data})


class DetalleFacturaView(APIView):
    """
    GET /api/v1/facturas/{id}/
    Detalle de una factura.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, factura_id):
        try:
            factura = FacturaElectronica.objects.get(pk=factura_id)
        except FacturaElectronica.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = FacturaElectronicaSerializer(factura)
        return Response(serializer.data)


class ReenviarFacturaView(APIView):
    """
    POST /api/v1/facturas/{id}/reenviar/
    Reintenta el envío al SRI para facturas en estado ERROR, RECHAZADA o PENDIENTE.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, factura_id):
        try:
            factura = FacturaElectronica.objects.get(pk=factura_id)
        except FacturaElectronica.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if factura.estado == 'AUTORIZADA':
            return Response(
                {'error': 'La factura ya está autorizada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from .services.sri import SriService
            SriService().procesar_factura(factura)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = FacturaElectronicaSerializer(factura)
        return Response(serializer.data)


class ConsultarAutorizacionView(APIView):
    """
    POST /api/v1/facturas/{id}/consultar/
    Consulta el estado de autorización directamente en el SRI.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, factura_id):
        try:
            factura = FacturaElectronica.objects.get(pk=factura_id)
        except FacturaElectronica.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            from .services.sri import SriService
            servicio = SriService()
            resp = servicio.consultar_autorizacion(factura.clave_acceso)
            estado_sri = resp.get('estado', '').upper()

            if not factura.respuesta_sri:
                factura.respuesta_sri = {}
            factura.respuesta_sri['ultima_consulta'] = resp

            if estado_sri == 'AUTORIZADO':
                factura.estado = 'AUTORIZADA'
                factura.numero_autorizacion = resp.get('numeroAutorizacion', '')
                factura.mensajes_sri = 'Autorizado correctamente.'
                fecha_str = resp.get('fechaAutorizacion', '')
                if fecha_str:
                    from datetime import datetime
                    try:
                        factura.fecha_autorizacion = datetime.strptime(
                            fecha_str, '%Y-%m-%dT%H:%M:%S'
                        ).replace(tzinfo=timezone.utc)
                    except ValueError:
                        factura.fecha_autorizacion = timezone.now()
            elif estado_sri in ('NO AUTORIZADO',):
                factura.estado = 'RECHAZADA'
                factura.mensajes_sri = '; '.join(
                    m.get('mensaje', '') for m in resp.get('mensajes', [])
                )

            factura.save()
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = FacturaElectronicaSerializer(factura)
        return Response(serializer.data)
