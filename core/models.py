from django.db import models
from django.contrib.auth.models import User
import random
import string

# --- 1. NUEVA ENTIDAD: COMPETICIÓN (La base de la nueva arquitectura) ---
class Competition(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre Liga/Copa") # Ej: Premier League
    slug = models.SlugField(unique=True, verbose_name="Identificador URL") # Ej: premier-league
    api_id = models.IntegerField(unique=True, verbose_name="ID en API Football") # Ej: 2021
    
    # Esto define si mostramos Tabla de Posiciones (Liga) o Grupos/Llaves (Copa)
    TYPE_CHOICES = [
        ('LEAGUE', 'Liga'), 
        ('CUP', 'Copa'),    
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='LEAGUE')

    def __str__(self):
        return self.name

# --- 2. EQUIPOS (Sin cambios, solo mantenemos tu estructura) ---
class Team(models.Model):
    name = models.CharField(max_length=50, verbose_name="Nombre")
    flag_code = models.CharField(max_length=5, verbose_name="Código Bandera") # Ej: "ar", "br"
    logo = models.URLField(null=True, blank=True, verbose_name="Escudo URL")
    
    def __str__(self):
        return self.name

# --- 3. PARTIDOS (Ahora con Competición y Ronda) ---
class Match(models.Model):
    # Relación nueva: Cada partido pertenece a una Liga/Copa específica
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='matches', verbose_name="Competición")
    
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches', verbose_name="Local")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches', verbose_name="Visitante")
    
    date = models.DateTimeField(verbose_name="Fecha del partido")
    status = models.CharField(max_length=20, default='SCHEDULED')
    
    # --- CAMPO NUEVO PARA TU FILTRO DE FECHAS ---
    # Aquí guardaremos "Regular Season - 1", "Group A - 3", "Quarter-finals", etc.
    round_name = models.CharField(max_length=50, verbose_name="Ronda / Fecha") 
    
    # Goles reales
    home_goals = models.IntegerField(null=True, blank=True, verbose_name="Goles Local")
    away_goals = models.IntegerField(null=True, blank=True, verbose_name="Goles Visitante")
    
    class Meta:
        verbose_name = "Partido"
        verbose_name_plural = "Partidos"

    def __str__(self):
        return f"[{self.competition.name}] {self.home_team} vs {self.away_team} ({self.round_name})"

# --- 4. PREDICCIONES (Tu lógica original intacta) ---
class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    
    predicted_home = models.IntegerField(verbose_name="Predicción Local")
    predicted_away = models.IntegerField(verbose_name="Predicción Visitante")
    points = models.IntegerField(default=0) 
    
    def __str__(self):
        return f"{self.user.username}: {self.predicted_home}-{self.predicted_away}"

    def get_score(self):
        """
        Calcula los puntos ganados comparando con el resultado real del partido.
        Retorna: 3 (Exacto), 1 (Tendencia), 0 (Nada) o None (Si no se jugó).
        """
        if self.match.home_goals is None or self.match.away_goals is None:
            return None

        ph = self.predicted_home
        pa = self.predicted_away
        rh = self.match.home_goals
        ra = self.match.away_goals

        # 1. Exacto (3 Puntos)
        if ph == rh and pa == ra:
            return 3

        # 2. Tendencia (1 Punto)
        gana_local = (ph > pa) and (rh > ra)
        gana_visitante = (ph < pa) and (rh < ra)
        empate = (ph == pa) and (rh == ra)

        if gana_local or gana_visitante or empate:
            return 1
        
        # 3. Nada
        return 0

# --- 5. TORNEOS (Actualizado con Competición y Rango de Fechas) ---
class Tournament(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre del Torneo")
    code = models.CharField(max_length=6, unique=True, verbose_name="Código de Invitación")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_tournaments")
    image = models.URLField(blank=True, null=True, verbose_name="Imagen (URL)")
    created_at = models.DateTimeField(auto_now_add=True)

    # --- NUEVOS FILTROS MAESTROS ---
    # Un torneo pertenece obligatoriamente a UNA competición (Premier, Champions, etc.)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, verbose_name="Liga/Copa Base")
    
    # Rango de fechas (Opcional: Si se dejan vacíos, incluye todo el torneo)
    start_round = models.CharField(max_length=50, null=True, blank=True, verbose_name="Desde la Ronda")
    end_round = models.CharField(max_length=50, null=True, blank=True, verbose_name="Hasta la Ronda")

    members = models.ManyToManyField(User, through='TournamentMember', related_name="tournaments")

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.competition.name})"

# --- 6. MIEMBROS (Sin cambios) ---
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
        unique_together = ('tournament', 'user')
        verbose_name = "Miembro de Torneo"
        verbose_name_plural = "Miembros de Torneo"

    def __str__(self):
        return f"{self.user.username} en {self.tournament.name} ({self.status})"
    
class Standing(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='standings')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    
    position = models.IntegerField(default=0)
    played = models.IntegerField(default=0)
    won = models.IntegerField(default=0)
    drawn = models.IntegerField(default=0)
    lost = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)
    goal_diff = models.IntegerField(default=0)
    
    # Para Mundiales o Champions (Ej: "GROUP_A")
    group = models.CharField(max_length=20, null=True, blank=True) 

    class Meta:
        ordering = ['group', 'position'] # Ordenar por grupo y posición

    def __str__(self):
        return f"{self.competition.name} - {self.team.name} ({self.points} pts)"