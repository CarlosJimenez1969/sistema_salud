from django.core.exceptions import PermissionDenied
from functools import wraps

def medico_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificamos el rol que definimos anteriormente
        if request.user.is_authenticated and request.user.role == 'MEDICO':
            return view_func(request, *args, **kwargs)
        raise PermissionDenied # Esto enviará a una página de error 403
    return _wrapped_view