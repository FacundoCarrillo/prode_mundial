from django import forms
from .models import Prediction, Tournament

class PredictionForm(forms.ModelForm):
    class Meta:
        model = Prediction
        fields = ['predicted_home', 'predicted_away']
        # Esto es solo estética para que se vea mejor
        widgets = {
            'predicted_home': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Local'}),
            'predicted_away': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Visitante'}),
        }
# --- EL NUEVO FORMULARIO PARA CREAR TORNEOS (AGREGAR ESTO) ---
class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'image'] # El usuario solo elige nombre e imagen
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-400',
                'placeholder': 'Ej: Copa de la Oficina'
            }),
            'image': forms.URLInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-400',
                'placeholder': 'https://... (Opcional)'
            })
        }