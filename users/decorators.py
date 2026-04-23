from django.core.exceptions import PermissionDenied
from functools import wraps

def medico_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verifica el campo 'role' que vimos en tu backup (MEDICO, ADMIN, SECRETARIA)
        if request.user.is_authenticated and request.user.role == 'MEDICO':
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view