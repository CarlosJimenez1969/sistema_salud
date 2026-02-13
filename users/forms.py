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

class RegistroMedicoForm(UserCreationForm):
    # --- 1. CAMPOS DE USUARIO PERSONALIZADOS ---
    first_name = forms.CharField(required=True, label="Nombres", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=True, label="Apellidos", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, label="Correo Electrónico", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    cedula = forms.CharField(required=True, label="Cédula", widget=forms.TextInput(attrs={'class': 'form-control'}))

    # --- 2. CAMPOS DEL PERFIL MÉDICO (EXTRA) ---
    especialidad = forms.ModelChoiceField(
        queryset=Especialidad.objects.all(),
        label="Especialidad",
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Seleccione su especialidad"
    )
    telefono_consultorio = forms.CharField(label="Teléfono Consultorio", widget=forms.TextInput(attrs={'class': 'form-control'}))
    direccion_consultorio = forms.CharField(label="Dirección", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))
    precio_consulta = forms.DecimalField(label="Costo por Cita ($)", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    
    # Widgets de hora HTML5 para que salga el relojito
    hora_inicio = forms.TimeField(label="Hora Inicio Jornada", widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}))
    hora_fin = forms.TimeField(label="Hora Fin Jornada", widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}))

    class Meta:
        model = User
        # Solo ponemos los campos que PERTENECEN al modelo User
        fields = ['username', 'first_name', 'last_name', 'email', 'cedula']

    # --- 3. LA MAGIA: GUARDADO ATÓMICO ---
    def save(self, commit=True):
        # Usamos transaction.atomic para asegurar que se creen LOS DOS o NINGUNO
        with transaction.atomic():
            # A) Guardamos el Usuario primero
            user = super().save(commit=False)
            
            # Asignamos roles y estados
            # (Asegúrate de que tu modelo User tenga estos campos, si no, bórralos)
            if hasattr(user, 'role'):
                user.role = User.Role.MEDICO
            if hasattr(user, 'pago_realizado'):
                user.pago_realizado = True  # Asumimos que si llena este form, ya pagó
            
            if commit:
                user.save()

                # B) Creamos el Perfil Médico vinculado
                Medico.objects.create(
                    usuario=user,
                    especialidad=self.cleaned_data['especialidad'],
                    telefono_consultorio=self.cleaned_data['telefono_consultorio'],
                    direccion_consultorio=self.cleaned_data['direccion_consultorio'],
                    precio_consulta=self.cleaned_data['precio_consulta'],
                    hora_inicio=self.cleaned_data['hora_inicio'],
                    hora_fin=self.cleaned_data['hora_fin']
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
    # Campos extra para confirmar contraseña
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data