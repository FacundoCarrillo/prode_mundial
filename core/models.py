from django.db import models
from django.contrib.auth.models import User
import uuid # <--- Agrega esto arriba de todo
import random
import string

# Modelo para los Equipos (Ej: Argentina, Brasil)
class Team(models.Model):
    name = models.CharField(max_length=50, verbose_name="Nombre")
    flag_code = models.CharField(max_length=5, verbose_name="Código Bandera") # Ej: "ar", "br"
    # Agregamos este campo nuevo. Usamos URLField porque guardamos el link, no el archivo.
    logo = models.URLField(null=True, blank=True, verbose_name="Escudo URL")
    def __str__(self):
        return self.name

# Modelo para los Partidos
class Match(models.Model):
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches', verbose_name="Local")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches', verbose_name="Visitante")
    date = models.DateTimeField(verbose_name="Fecha del partido")
    
    # Goles reales (nulos hasta que se juegue)
    home_goals = models.IntegerField(null=True, blank=True, verbose_name="Goles Local")
    away_goals = models.IntegerField(null=True, blank=True, verbose_name="Goles Visitante")
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"

# Modelo para las Predicciones de los usuarios
class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # Relación con el usuario de Django
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    
    predicted_home = models.IntegerField(verbose_name="Predicción Local")
    predicted_away = models.IntegerField(verbose_name="Predicción Visitante")
    # --- AGREGA ESTA LÍNEA NUEVA ---
    points = models.IntegerField(default=0) 
    # -------------------------------
    
    def __str__(self):
        return f"{self.user.username}: {self.predicted_home}-{self.predicted_away}"
    def get_score(self):
        """
        Calcula los puntos ganados comparando con el resultado real del partido.
        Retorna: 3 (Exacto), 1 (Tendencia), 0 (Nada) o None (Si no se jugó).
        """
        # Si el partido no tiene resultado cargado aún, no hay puntos
        if self.match.home_goals is None or self.match.away_goals is None:
            return None

        # Alias para escribir menos
        ph = self.predicted_home
        pa = self.predicted_away
        rh = self.match.home_goals
        ra = self.match.away_goals

        # 1. Exacto (3 Puntos)
        if ph == rh and pa == ra:
            return 3

        # 2. Tendencia (1 Punto)
        # Gana Local (Ambos predicen local > visitante)
        gana_local = (ph > pa) and (rh > ra)
        # Gana Visitante (Ambos predicen local < visitante)
        gana_visitante = (ph < pa) and (rh < ra)
        # Empate (Ambos predicen empate, pero no fue exacto porque ya pasó el if de arriba)
        empate = (ph == pa) and (rh == ra)

        if gana_local or gana_visitante or empate:
            return 1
        
        # 3. Nada
        return 0
class Tournament(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre del Torneo")
    # Generamos un código único corto (Ej: "A7X9") para compartir
    code = models.CharField(max_length=6, unique=True, verbose_name="Código de Invitación")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_tournaments")
    image = models.URLField(blank=True, null=True, verbose_name="Imagen (URL)")
    created_at = models.DateTimeField(auto_now_add=True)

    # Relación con usuarios a través de la tabla intermedia
    members = models.ManyToManyField(User, through='TournamentMember', related_name="tournaments")

    def save(self, *args, **kwargs):
        # Si no tiene código, generamos uno aleatorio de 6 letras/números
        if not self.code:
            self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class TournamentMember(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente de Aprobación'),
        ('ACCEPTED', 'Aceptado / Jugando'),
        ('REJECTED', 'Rechazado'),
    ]

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    # Puntaje acumulado SOLO en este torneo
    points = models.IntegerField(default=0) 

    class Meta:
        # Evita que un usuario se una dos veces al mismo torneo
        unique_together = ('tournament', 'user')
        verbose_name = "Miembro de Torneo"
        verbose_name_plural = "Miembros de Torneo"

    def __str__(self):
        return f"{self.user.username} en {self.tournament.name} ({self.status})"
