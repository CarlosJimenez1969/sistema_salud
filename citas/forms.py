from django import forms
from .models import Cita

class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        # Asegúrate de incluir 'paciente' si la secretaria debe seleccionarlo
        fields = ['medico', 'paciente', 'fecha', 'hora', 'motivo', 'estado']
        
        widgets = {
            'medico': forms.Select(attrs={'class': 'form-select'}),
            'paciente': forms.Select(attrs={'class': 'form-select select2'}), # Recomendado Select2 para buscar pacientes
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'motivo': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Breve descripción del motivo...'
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos el médico si se pasa desde la vista
        medico_fijo = kwargs.pop('medico_fijo', None)
        super().__init__(*args, **kwargs)
        
        if medico_fijo:
            # 1. Establecemos el médico vinculado como el valor inicial
            self.fields['medico'].initial = medico_fijo
            
            # 2. Limitamos las opciones del dropdown solo a ese médico
            self.fields['medico'].queryset = self.fields['medico'].queryset.filter(id=medico_fijo.id)
            
            # 3. Lo hacemos obligatorio y opcionalmente bloqueamos el widget
            self.fields['medico'].widget.attrs['readonly'] = True
            
            # Si quieres que ni siquiera puedan intentar cambiarlo en el HTML:
            self.fields['medico'].empty_label = None