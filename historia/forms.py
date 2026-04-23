from django import forms
from .models import HistoriaClinica, Receta, Triaje

class HistoriaForm(forms.ModelForm):
    tipo_diagnostico = forms.ChoiceField(
        choices=[('', '-- Seleccionar --'), ('PRESUNTIVO', 'Presuntivo'), ('DEFINITIVO', 'Definitivo')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
    )

    class Meta:
        model = HistoriaClinica
        fields = [
            'motivo_consulta', 'enfermedad_actual',
            'antecedentes_personales', 'antecedentes_familiares', 'revision_sistemas',
            'temperatura', 'presion_arterial', 'pulso', 'peso', 'altura',
            'examen_fisico', 'tipo_diagnostico', 'diagnostico', 'tratamiento',
            'plan_educacional', 'proxima_cita_control', 'signos_alarma'
        ]

        widgets = {
            # Seccion 1
            'motivo_consulta': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'enfermedad_actual': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # Antecedentes
            'antecedentes_personales': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                'placeholder': 'Ej: HTA (10 años), DM2 (5 años), alérgico a penicilina, toma Metformina 850mg...'}),
            'antecedentes_familiares': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                'placeholder': 'Ej: Padre con DM2, madre con HTA, hermano con cardiopatía...'}),
            'revision_sistemas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                'placeholder': 'Ej: CV: sin dolor torácico. Resp: sin disnea. GI: náuseas (+). SNC: sin cefalea...'}),
            
            # Seccion 2: Signos Vitales
            'temperatura': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '°C'}),
            'presion_arterial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '120/80'}),
            'pulso': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'LPM'}),
            'peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Kg'}),
            'altura': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'm/cm'}),
            
            # Seccion 3: Examen y Diagnostico
            'examen_fisico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo_diagnostico': forms.Select(attrs={'class': 'form-select'}),
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                'placeholder': 'Ej: J06.9 Infección aguda de vías respiratorias superiores...'}),
            'tratamiento': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Receta e indicaciones...'}),
            'plan_educacional': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                'placeholder': 'Ej: Se instruye sobre dieta baja en sodio, ejercicio 30min/día, no automedicarse...'}),
            
            # Seguimiento
            'proxima_cita_control': forms.DateTimeInput(attrs={
                    'class': 'form-control border-primary shadow-sm',
                    'placeholder': 'Seleccione día y hora...',
                    'autocomplete': 'off'
                },
                format='%Y-%m-%d %H:%M'
            ),

            # --- ACTUALIZACIÓN AQUÍ: Signos de Alarma con Placeholder ---
            'signos_alarma': forms.Textarea(attrs={
                'class': 'form-control border-danger',
                'rows': 3,
                'placeholder': 'Escriba aquí los signos de alarma o deje vacío para usar el texto estándar...',
                'value': '', # Forzamos que esté vacío al cargar
            }),
        }

class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = ['prescripcion', 'indicaciones_generales']
        widgets = {
            'prescripcion': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6, 
                'placeholder': 'Ej: Paracetamol 500mg - 1 tableta cada 8 horas por 3 días'
            }),
            'indicaciones_generales': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Ej: Beber abundante agua y guardar reposo.'
            }),
        }

class TriajeForm(forms.ModelForm):
    class Meta:
        model = Triaje
        fields = ['peso', 'talla', 'presion_arterial', 'frecuencia_cardiaca', 'temperatura', 'saturacion_oxigeno']
        widgets = {
            'peso':               forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ej: 70.5'}),
            'talla':              forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Ej: 165'}),
            'presion_arterial':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 120/80'}),
            'frecuencia_cardiaca':forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'LPM'}),
            'temperatura':        forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '°C'}),
            'saturacion_oxigeno': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '% SpO2'}),
        }
        labels = {
            'peso':               'Peso (kg)',
            'talla':              'Talla (cm)',
            'presion_arterial':   'Presión Arterial',
            'frecuencia_cardiaca':'Frecuencia Cardíaca (LPM)',
            'temperatura':        'Temperatura (°C)',
            'saturacion_oxigeno': 'Saturación O2 (%)',
        }