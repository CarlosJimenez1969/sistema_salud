from django import forms
from django.contrib.auth.password_validation import validate_password
from users.models import User
from .models import Paciente

TIPOS_SANGRE = [
    ('', '— Seleccione —'),
    ('A+', 'A+'), ('A-', 'A-'),
    ('B+', 'B+'), ('B-', 'B-'),
    ('AB+', 'AB+'), ('AB-', 'AB-'),
    ('O+', 'O+'), ('O-', 'O-'),
]

class PacienteForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombres", required=True)
    last_name = forms.CharField(label="Apellidos", required=True)
    cedula = forms.CharField(label="Cédula", required=True)
    email = forms.EmailField(label="Correo Electrónico", required=True)
    tipo_sangre = forms.ChoiceField(label="Tipo de Sangre", choices=TIPOS_SANGRE, required=False)

    class Meta:
        model = Paciente
        fields = ['fecha_nacimiento', 'sexo', 'telefono', 'tipo_sangre', 'alergias', 'enfermedades_cronicas', 'direccion']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'alergias': forms.Textarea(attrs={'rows': 2}),
            'enfermedades_cronicas': forms.Textarea(attrs={'rows': 2}),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Av. Amazonas y Colon, Edificio 1',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.usuario.first_name
            self.fields['last_name'].initial = self.instance.usuario.last_name
            self.fields['cedula'].initial = self.instance.usuario.cedula
            self.fields['email'].initial = self.instance.usuario.email

    def clean_cedula(self):
        cedula = (self.cleaned_data.get('cedula') or '').strip()
        if not cedula:
            raise forms.ValidationError("La cédula es obligatoria.")
        if not cedula.isdigit() or not (8 <= len(cedula) <= 13):
            raise forms.ValidationError("La cédula debe tener entre 8 y 13 dígitos numéricos.")
        # Excluir el usuario actual si estamos editando
        qs = User.objects.filter(cedula=cedula)
        if self.instance and self.instance.pk:
            qs = qs.exclude(id=self.instance.usuario_id)
        if qs.exists():
            raise forms.ValidationError(
                "Ya existe un paciente con esta cédula en el sistema. Búsquelo en el listado de pacientes."
            )
        return cedula

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError("El correo es obligatorio.")
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(id=self.instance.usuario_id)
        if qs.exists():
            raise forms.ValidationError(
                "Ya existe un usuario registrado con este correo. Use otro correo o busque al paciente existente."
            )
        return email

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


W = {'class': 'form-control'}

class RegistroPacienteForm(forms.Form):
    first_name  = forms.CharField(label="Nombres",    widget=forms.TextInput(attrs={**W, 'placeholder': 'Tus nombres'}))
    last_name   = forms.CharField(label="Apellidos",  widget=forms.TextInput(attrs={**W, 'placeholder': 'Tus apellidos'}))
    cedula      = forms.CharField(label="Cédula / Pasaporte", widget=forms.TextInput(attrs={**W, 'placeholder': 'Número de identificación'}))
    email       = forms.EmailField(label="Correo Electrónico", widget=forms.EmailInput(attrs={**W, 'placeholder': 'correo@ejemplo.com'}))
    telefono    = forms.CharField(label="Teléfono", required=False, widget=forms.TextInput(attrs={**W, 'placeholder': 'Ej: 0991234567'}))
    direccion   = forms.CharField(label="Dirección", required=False, widget=forms.TextInput(attrs={**W, 'placeholder': 'Ej: Av. Amazonas y Colón, Edificio 1'}))
    fecha_nacimiento = forms.DateField(label="Fecha de Nacimiento", widget=forms.DateInput(attrs={**W, 'type': 'date'}))
    sexo = forms.ChoiceField(
        label="Sexo",
        choices=[('', '— Seleccione —'), ('M', 'Masculino'), ('F', 'Femenino')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    password1 = forms.CharField(label="Contraseña",         widget=forms.PasswordInput(attrs={**W, 'placeholder': 'Mínimo 8 caracteres'}))
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput(attrs={**W, 'placeholder': 'Repite la contraseña'}))

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    def clean_cedula(self):
        cedula = self.cleaned_data['cedula'].strip()
        if not cedula.isdigit() or not (8 <= len(cedula) <= 13):
            raise forms.ValidationError("La cédula/pasaporte debe contener entre 8 y 13 dígitos numéricos.")
        if User.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Esta cédula ya está registrada.")
        return cedula

    def clean_password1(self):
        pwd = self.cleaned_data.get('password1')
        if pwd:
            validate_password(pwd)
        return pwd

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Las contraseñas no coinciden.")
        return cleaned

    def save(self):
        d = self.cleaned_data
        user = User.objects.create_user(
            username=d['email'],
            email=d['email'],
            password=d['password1'],
            first_name=d['first_name'],
            last_name=d['last_name'],
            cedula=d['cedula'],
            role=User.Role.PACIENTE,
        )
        from .models import Paciente
        Paciente.objects.create(
            usuario=user,
            fecha_nacimiento=d['fecha_nacimiento'],
            sexo=d['sexo'],
            telefono=d.get('telefono', ''),
            direccion=d.get('direccion', ''),
        )
        return user