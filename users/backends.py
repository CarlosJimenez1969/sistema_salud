from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class UsernameOrEmailBackend(ModelBackend):
    """Permite autenticarse con username o email indistintamente."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # Buscar por username primero, luego por email
        user = (
            User.objects.filter(username=username).first()
            or User.objects.filter(email=username).first()
        )

        if user and user.check_password(password):
            return user
        return None
