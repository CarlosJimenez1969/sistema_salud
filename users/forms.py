from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class RegistroMedicoForm(UserCreationForm):
    # Añadimos los campos obligatorios para el registro
    first_name = forms.CharField(required=True, label="Nombres")
    last_name = forms.CharField(required=True, label="Apellidos")
    email = forms.EmailField(required=True, label="Correo Electrónico")
    cedula = forms.CharField(required=True, label="Cédula")

    class Meta:
        model = User
        # Definimos qué campos mostrar en el HTML
        fields = ['first_name', 'last_name', 'cedula', 'email']

    def save(self, commit=True):
        # Guardamos el usuario pero forzamos que sea MÉDICO
        user = super().save(commit=False)
        user.role = User.Role.MEDICO
        user.pago_realizado = False # Aún no paga
        if commit:
            user.save()
        return user