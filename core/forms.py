from django import forms
from .models import Prediction

class PredictionForm(forms.ModelForm):
    class Meta:
        model = Prediction
        fields = ['predicted_home', 'predicted_away']
        # Esto es solo estética para que se vea mejor
        widgets = {
            'predicted_home': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Local'}),
            'predicted_away': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Visitante'}),
        }