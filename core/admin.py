from django.contrib import admin
from .models import Team, Match, Prediction, Tournament, TournamentMember, Competition

# --- 1. NUEVA CONFIGURACIÓN PARA COMPETICIONES ---
@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'api_id', 'slug')
    list_filter = ('type',)
    search_fields = ('name',)
    # Esto hace que el slug se escriba solo mientras escribís el nombre
    prepopulated_fields = {"slug": ("name",)} 

# --- 2. CONFIGURACIÓN MEJORADA PARA PARTIDOS ---
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    # Ahora mostramos la Competición y la Ronda en la lista
    list_display = ('__str__', 'competition', 'round_name', 'date', 'status')
    list_filter = ('competition', 'status', 'date') # Filtros laterales muy útiles
    search_fields = ('home_team__name', 'away_team__name')

# --- 3. CONFIGURACIÓN MEJORADA PARA TORNEOS ---
class MemberInline(admin.TabularInline):
    model = TournamentMember
    extra = 1

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'competition', 'creator', 'created_at')
    list_filter = ('competition',) # Filtro lateral para ver torneos por liga
    search_fields = ('name', 'code')
    inlines = [MemberInline]

# --- 4. RESTO DE MODELOS (Sin cambios mayores) ---
admin.site.register(Team)
admin.site.register(Prediction)

@admin.register(TournamentMember)
class TournamentMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'tournament', 'status', 'points')
    list_filter = ('status', 'tournament__competition') # Filtramos por la liga del torneo