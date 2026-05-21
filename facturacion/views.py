from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count

from .models import FacturaElectronica


@login_required
def lista_facturas(request):
    role = getattr(request.user, 'role', '')

    if role == 'ADMIN':
        facturas = FacturaElectronica.objects.select_related('medico__usuario').all()
    elif role == 'MEDICO':
        try:
            facturas = FacturaElectronica.objects.filter(medico=request.user.perfil_medico)
        except Exception:
            facturas = FacturaElectronica.objects.none()
    else:
        messages.error(request, 'No tienes permiso para ver las facturas.')
        return redirect('home')

    estado_filtro = request.GET.get('estado', '')
    buscar        = request.GET.get('q', '').strip()
    fecha_desde   = request.GET.get('fecha_desde', '')
    fecha_hasta   = request.GET.get('fecha_hasta', '')

    if estado_filtro:
        facturas = facturas.filter(estado=estado_filtro)
    if buscar:
        facturas = (
            facturas.filter(receptor_nombre__icontains=buscar) |
            facturas.filter(receptor_identificacion__icontains=buscar) |
            facturas.filter(numero_secuencial__icontains=buscar)
        )
    if fecha_desde:
        facturas = facturas.filter(fecha_emision__date__gte=fecha_desde)
    if fecha_hasta:
        facturas = facturas.filter(fecha_emision__date__lte=fecha_hasta)

    facturas = facturas.order_by('-fecha_emision')

    # Totales por estado
    resumen = {v: facturas.filter(estado=v).aggregate(
        cantidad=Count('id'), total=Sum('total')
    ) for v, _ in FacturaElectronica.ESTADOS}

    # Totales globales EXCLUYENDO anuladas (las anuladas no son fiscalmente activas)
    activas = facturas.exclude(estado='ANULADA')

    return render(request, 'facturacion/lista_facturas.html', {
        'facturas':      facturas,
        'estado_filtro': estado_filtro,
        'buscar':        buscar,
        'fecha_desde':   fecha_desde,
        'fecha_hasta':   fecha_hasta,
        'estados':       FacturaElectronica.ESTADOS,
        'resumen':       resumen,
        'total_activas': activas.count(),
        'total_general': activas.aggregate(t=Sum('total'))['t'] or 0,
    })


@login_required
def detalle_factura(request, factura_id):
    """Detalle completo de una factura: XML, respuesta SRI, mensajes."""
    role = getattr(request.user, 'role', '')

    if role == 'ADMIN':
        factura = get_object_or_404(FacturaElectronica, id=factura_id)
    elif role == 'MEDICO':
        try:
            factura = get_object_or_404(
                FacturaElectronica, id=factura_id, medico=request.user.perfil_medico
            )
        except Exception:
            messages.error(request, 'No tienes permiso para ver esta factura.')
            return redirect('lista_facturas')
    else:
        messages.error(request, 'Acceso denegado.')
        return redirect('home')

    return render(request, 'facturacion/detalle_factura.html', {'factura': factura})


@login_required
def reenviar_factura(request, factura_id):
    """Reintenta el proceso completo para facturas en estado ERROR, RECHAZADA o PENDIENTE."""
    if getattr(request.user, 'role', '') != 'ADMIN':
        messages.error(request, 'Solo el administrador puede reenviar facturas.')
        return redirect('lista_facturas')

    factura = get_object_or_404(FacturaElectronica, id=factura_id)

    if factura.estado == 'AUTORIZADA':
        messages.warning(request, 'Esta factura ya está autorizada.')
        return redirect('detalle_factura', factura_id=factura_id)

    if request.method == 'POST':
        try:
            from .services.sri import SriService
            servicio = SriService()
            servicio.procesar_factura(factura)
            messages.success(request, f'Factura {factura.numero_secuencial} reenviada. Estado: {factura.get_estado_display()}')
        except Exception as e:
            messages.error(request, f'Error al reenviar: {e}')
        return redirect('detalle_factura', factura_id=factura_id)

    return render(request, 'facturacion/confirmar_reenvio.html', {'factura': factura})


@login_required
def consultar_autorizacion(request, factura_id):
    """Consulta manualmente el estado de autorización en el SRI."""
    if getattr(request.user, 'role', '') != 'ADMIN':
        messages.error(request, 'Acceso denegado.')
        return redirect('lista_facturas')

    factura = get_object_or_404(FacturaElectronica, id=factura_id)

    try:
        from .services.sri import SriService
        servicio = SriService()
        resp = servicio.consultar_autorizacion(factura.clave_acceso)
        estado = resp.get('estado', '').upper()

        if not factura.respuesta_sri:
            factura.respuesta_sri = {}
        factura.respuesta_sri['ultima_consulta'] = resp

        if estado == 'AUTORIZADO':
            factura.estado = 'AUTORIZADA'
            factura.numero_autorizacion = resp.get('numeroAutorizacion', '')
            factura.mensajes_sri = 'Autorizado correctamente.'
            fecha_str = resp.get('fechaAutorizacion', '')
            if fecha_str:
                try:
                    from datetime import datetime
                    factura.fecha_autorizacion = datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M:%S').replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    factura.fecha_autorizacion = timezone.now()
        elif estado in ('NO AUTORIZADO',):
            factura.estado = 'RECHAZADA'
            factura.mensajes_sri = '; '.join(m.get('mensaje', '') for m in resp.get('mensajes', []))

        factura.save()
        messages.success(request, f'Consulta realizada. Estado SRI: {estado}')
    except Exception as e:
        messages.error(request, f'Error al consultar el SRI: {e}')

    return redirect('detalle_factura', factura_id=factura_id)
