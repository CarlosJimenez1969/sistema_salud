from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout

class SeguridadSesionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Si el sistema devuelve un error 403 (Prohibido), cerramos sesión por seguridad
        if response.status_code == 403:
            logout(request)
            messages.error(request, "Tu sesión ha expirado o no tienes permisos. Por favor, ingresa de nuevo.")
            return redirect('login')

        return response