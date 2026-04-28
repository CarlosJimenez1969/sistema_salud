from pyexpat.errors import messages
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import redirect, render
from medico.models import Medico, Especialidad
from django.contrib.auth.decorators import login_required

from django.contrib.auth.models import Group
#from .forms import MedicoRegistroForm, SecretariaRegistroForm

User = get_user_model()

class RegistroInicialMedicoForm(forms.ModelForm):
    # Definimos los widgets para que aparezcan las cajas de texto con estilo
    username = forms.CharField(label="Usuario", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: dr_ivan'}))
    first_name = forms.CharField(label="Nombres", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tus nombres'}))
    last_name = forms.CharField(label="Apellidos", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tus apellidos'}))
    email = forms.EmailField(label="Correo Electrónico", widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}))
    cedula = forms.CharField(label="Cédula", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de identificación'}))
    especialidad = forms.ModelChoiceField(
        queryset=Especialidad.objects.all().order_by('nombre'),
        label="Especialidad Médica",
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Seleccione su especialidad"
    )
    pais = forms.CharField(
        label="País", initial="Ecuador",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Ecuador'})
    )
    ciudad = forms.CharField(
        label="Ciudad",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Quito'})
    )
    sector = forms.ChoiceField(
        label="Sector",
        choices=[('', '-- Seleccionar --'), ('NORTE', 'Norte'), ('CENTRO', 'Centro'), ('SUR', 'Sur'), ('VALLES', 'Valles'), ('OTRO', 'Otro')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'cedula', 'especialidad', 'pais', 'ciudad', 'sector']

    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            if not user.role or user.role == user.base_role:
                user.role = 'MEDICO'
            user.pago_realizado = False
            user.set_unusable_password()
            if commit:
                user.save()
                from medico.models import Medico
                Medico.objects.create(
                    usuario=user,
                    especialidad=self.cleaned_data['especialidad'],
                    pais=self.cleaned_data.get('pais', 'Ecuador'),
                    ciudad=self.cleaned_data.get('ciudad', ''),
                    sector=self.cleaned_data.get('sector', ''),
                )
        return user
    
# --- VISTA 2: MÉDICO CREA SECRETARIA ---
@login_required
def crear_secretaria(request):
    # Verificamos que quien entra sea un Médico
    if not hasattr(request.user, 'perfil_medico'):
        messages.error(request, "Solo los médicos pueden registrar secretarias.")
        return redirect('home')

    if request.method == 'POST':
        form = SecretariaRegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            
            # --- LA CLAVE: Darle permisos ---
            user.is_staff = True  # Le damos permiso de Staff para agendar
            user.save()
            
            # Opcional: Agregar al grupo "Secretarias" si existe
            # grupo, created = Group.objects.get_or_create(name='Secretarias')
            # user.groups.add(grupo)

            messages.success(request, f'Secretaria {user.username} creada correctamente.')
            return redirect('home') # O volver al perfil del médico
    else:
        form = SecretariaRegistroForm()

    return render(request, 'crear_secretaria.html', {'form': form})

class SecretariaRegistroForm(forms.ModelForm):
    class Meta:
        model = User
        # Añadimos 'cedula' a la lista de campos
        fields = ['username', 'first_name', 'last_name', 'email', 'cedula']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuario'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo Electrónico'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de Cédula'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    # Validación adicional para la cédula
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if User.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Esta cédula ya está registrada en el sistema.")
        return cedula
    
class CompletarPerfilMedicoForm(forms.Form): # Usamos forms.Form porque el User ya existe
    especialidad = forms.ModelChoiceField(
        queryset=Especialidad.objects.all(),
        label="Especialidad",
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Seleccione su especialidad"
    )
    telefono_consultorio = forms.CharField(label="Teléfono Consultorio", widget=forms.TextInput(attrs={'class': 'form-control'}))
    direccion_consultorio = forms.CharField(label="Dirección", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))
    precio_consulta = forms.DecimalField(label="Costo por Cita ($)", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    hora_inicio = forms.TimeField(label="Hora Inicio", widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}))
    hora_fin = forms.TimeField(label="Hora Fin", widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}))

    def save_perfil(self, user):
        with transaction.atomic():
            return Medico.objects.create(
                usuario=user,
                especialidad=self.cleaned_data['especialidad'],
                telefono_consultorio=self.cleaned_data['telefono_consultorio'],
                direccion_consultorio=self.cleaned_data['direccion_consultorio'],
                precio_consulta=self.cleaned_data['precio_consulta'],
                hora_inicio=self.cleaned_data['hora_inicio'],
                hora_fin=self.cleaned_data['hora_fin']
            )