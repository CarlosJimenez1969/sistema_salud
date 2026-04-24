from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from functools import wraps
from .models import Medico

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

        if not hora_inicio or not hora_fin:
            messages.error(request, "Debe ingresar hora de inicio y hora de fin.")
        elif hora_inicio >= hora_fin:
            messages.error(request, "La hora de inicio debe ser menor a la hora de fin.")
        else:
            medico.hora_inicio = hora_inicio
            medico.hora_fin = hora_fin
            medico.intervalo_minutos = int(intervalo)
            medico.save()
            messages.success(request, "Horario de atención actualizado correctamente.")
            return redirect('home')

    return render(request, 'configurar_horario.html', {'medico': medico})
