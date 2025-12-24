from django import forms
from django.contrib.auth.models import User  # <--- IMPORTANTE: Agregamos esto
from .models import Prediction, Tournament, Match

class PredictionForm(forms.ModelForm):
    class Meta:
        model = Prediction
        fields = ['predicted_home', 'predicted_away']
        widgets = {
            'predicted_home': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Local'}),
            'predicted_away': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Visitante'}),
        }

class TournamentForm(forms.ModelForm):
    # Agregamos los campos para elegir inicio y fin (ChoiceField crea un dropdown)
    start_round = forms.ChoiceField(required=False, label="Desde la fecha")
    end_round = forms.ChoiceField(required=False, label="Hasta la fecha")

    class Meta:
        model = Tournament
        fields = ['name', 'image', 'start_round', 'end_round']
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

    def __init__(self, *args, **kwargs):
        # Extraemos la competición que pasaremos desde la vista
        competition = kwargs.pop('competition', None)
        super().__init__(*args, **kwargs)

        if competition:
            # Buscamos todas las rondas ÚNICAS de esa liga
            rondas = Match.objects.filter(competition=competition).values_list('round_name', flat=True).distinct().order_by('date')
            
            # Las convertimos en opciones para el select [(valor, texto), ...]
            opciones = [('', 'Torneo Completo (Todas las fechas)')] + [(r, r) for r in rondas]
            
            self.fields['start_round'].choices = opciones
            self.fields['end_round'].choices = opciones
            
            # Estilos CSS para los select
            style = 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-400 bg-white'
            self.fields['start_round'].widget.attrs['class'] = style
            self.fields['end_round'].widget.attrs['class'] = style

# --- NUEVO FORMULARIO PARA EDITAR PERFIL ---
class EditarPerfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-slate-500 focus:border-slate-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-slate-500 focus:border-slate-500 bg-gray-100 text-gray-500', 'readonly': 'readonly'}), 
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-slate-500 focus:border-slate-500'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-slate-500 focus:border-slate-500'}),
        }
    
    def clean_email(self):
        # Evita que cambien el email (importante si usas Google Login)
        return self.instance.email