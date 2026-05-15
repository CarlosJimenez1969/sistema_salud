"""Variables disponibles en todos los templates."""
from django.conf import settings


def analytics(request):
    """Hace disponible el ID de Google Analytics en todos los templates."""
    return {
        'GOOGLE_ANALYTICS_ID': getattr(settings, 'GOOGLE_ANALYTICS_ID', ''),
    }
