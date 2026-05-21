from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from functools import wraps
from .models import Medico, Pais, Ciudad

def medico_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'MEDICO':
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view


@login_required
def configurar_horario(request):
    try:
        medico = request.user.perfil_medico
    except AttributeError:
        messages.error(request, "Acceso denegado.")
        return redirect('home')

    if request.method == 'POST':
        hora_inicio = request.POST.get('hora_inicio')
        hora_fin = request.POST.get('hora_fin')
        intervalo = request.POST.get('intervalo_minutos', 30)
        precio = (request.POST.get('precio_consulta') or '').strip()

        if not hora_inicio or not hora_fin:
            messages.error(request, "Debe ingresar hora de inicio y hora de fin.")
        elif hora_inicio >= hora_fin:
            messages.error(request, "La hora de inicio debe ser menor a la hora de fin.")
        else:
            from decimal import Decimal, InvalidOperation
            medico.hora_inicio = hora_inicio
            medico.hora_fin = hora_fin
            medico.intervalo_minutos = int(intervalo)
            if precio:
                try:
                    medico.precio_consulta = Decimal(precio)
                except InvalidOperation:
                    messages.error(request, "Precio de consulta inválido.")
                    return render(request, 'configurar_horario.html', {'medico': medico})
            medico.save()
            messages.success(request, "Horario y precio de consulta actualizados correctamente.")
            return redirect('home')

    return render(request, 'configurar_horario.html', {'medico': medico})


def ciudades_por_pais(request):
    """Devuelve ciudades de un país. Endpoint público usado en formularios de registro."""
    pais_id = request.GET.get('pais_id')
    ciudades = Ciudad.objects.filter(pais_id=pais_id).values('id', 'nombre') if pais_id else []
    return JsonResponse(list(ciudades), safe=False)
