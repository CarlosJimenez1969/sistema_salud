from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout


class ReferrerPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Referrer-Policy'] = 'unsafe-url'
        return response


class SeguridadSesionMiddleware:
    # URLs que no deben ser interceptadas por el manejador de 403
    URLS_EXCLUIDAS = ('/cron/', '/api/', '/admin/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Excluir endpoints de API/cron/admin del manejo automático de 403
        if any(request.path.startswith(p) for p in self.URLS_EXCLUIDAS):
            return response

        # Si el sistema devuelve un error 403 (Prohibido), cerramos sesión por seguridad
        if response.status_code == 403:
            logout(request)
            messages.error(request, "Tu sesión ha expirado o no tienes permisos. Por favor, ingresa de nuevo.")
            return redirect('login')

        return response


class SuscripcionMiddleware:
    """Bloquea acceso a médicos cuya suscripción ya venció (los redirige al pago)."""

    # URLs siempre permitidas (login, logout, pago, recursos estáticos)
    URLS_PERMITIDAS = (
        '/admin/', '/login/', '/logout/', '/accounts/', '/static/', '/media/',
        '/renovar-suscripcion/', '/pasarela-pago/', '/confirmar-pago/',
        '/registro-exitoso/', '/contacto/', '/api/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, 'role', '') == 'MEDICO':
            # Solo aplicamos a médicos
            if not any(request.path.startswith(p) for p in self.URLS_PERMITIDAS):
                if hasattr(request.user, 'perfil_medico'):
                    medico = request.user.perfil_medico
                    if medico.fecha_fin_suscripcion and not medico.suscripcion_activa:
                        messages.warning(request, "Tu suscripción venció. Renueva para continuar usando el sistema.")
                        return redirect('renovar_suscripcion')
        return self.get_response(request)