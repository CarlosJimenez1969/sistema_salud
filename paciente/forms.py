from django import forms
from users.models import User
from .models import Paciente

class PacienteForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombres", required=True)
    last_name = forms.CharField(label="Apellidos", required=True)
    cedula = forms.CharField(label="Cédula", required=True)
    email = forms.EmailField(label="Correo Electrónico", required=True)

    class Meta:
        model = Paciente
        fields = ['fecha_nacimiento', 'telefono', 'tipo_sangre', 'alergias', 'enfermedades_cronicas']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'alergias': forms.Textarea(attrs={'rows': 2}),
            'enfermedades_cronicas': forms.Textarea(attrs={'rows': 2}),
        }

    # --- NUEVO: ESTO CARGA LOS DATOS AL EDITAR ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estamos editando un paciente existente (tiene ID)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.usuario.first_name
            self.fields['last_name'].initial = self.instance.usuario.last_name
            self.fields['cedula'].initial = self.instance.usuario.cedula
            self.fields['email'].initial = self.instance.usuario.email
            # El email y cédula no deberían cambiarse fácilmente, pero por ahora lo dejamos editable

    def save(self, commit=True):
        # Si el paciente YA EXISTE, solo actualizamos
        if self.instance.pk:
            user = self.instance.usuario
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.cedula = self.cleaned_data['cedula']
            user.email = self.cleaned_data['email']
            user.save()
            paciente = super().save(commit=False)
        else:
            # Si es NUEVO, creamos el usuario (Lógica anterior)
            user = User.objects.create_user(
                username=self.cleaned_data['email'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['cedula'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                cedula=self.cleaned_data['cedula'],
                role=User.Role.PACIENTE
            )
            paciente = super().save(commit=False)
            paciente.usuario = user
        
        if commit:
            paciente.save()
        return paciente