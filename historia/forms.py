from django import forms
from .models import HistoriaClinica

class HistoriaForm(forms.ModelForm):
    class Meta:
        model = HistoriaClinica
        # Excluimos lo que se llena automático (paciente, médico, fecha)
        exclude = ['paciente', 'medico', 'fecha_atencion']
        
        widgets = {
            # Hacemos las cajas de texto más grandes para escribir cómodamente
            'motivo_consulta': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'enfermedad_actual': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'examen_fisico': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'diagnostico': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Código CIE-10 o descripción'}),
            'tratamiento': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            
            # Signos vitales más pequeños
            'temperatura': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'altura': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'presion_arterial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '120/80'}),
            'pulso': forms.NumberInput(attrs={'class': 'form-control'}),
        }