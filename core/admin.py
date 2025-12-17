from django.contrib import admin
from .models import Team, Match, Prediction, Tournament, TournamentMember

admin.site.register(Team)
admin.site.register(Match)
admin.site.register(Prediction)
# Configuración para ver los miembros DENTRO de la pantalla del torneo
class MemberInline(admin.TabularInline):
    model = TournamentMember
    extra = 1

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'creator', 'created_at')
    search_fields = ('name', 'code')
    inlines = [MemberInline] # Esto permite agregar gente desde el torneo

@admin.register(TournamentMember)
class TournamentMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'tournament', 'status', 'points')
    list_filter = ('status', 'tournament')