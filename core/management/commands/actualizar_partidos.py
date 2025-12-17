from django.core.management.base import BaseCommand
from core.models import Match
import requests
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Actualiza partidos usando football-data.org'

    def handle(self, *args, **kwargs):
        self.stdout.write("📡 Conectando a Football-Data.org...")

        # --- TU NUEVA CLAVE AQUÍ ---
        # Reemplaza esto con la clave que te llegó al mail
        API_TOKEN = '1988cfde850245faaaceaf5d9ff33ada' 
        # ---------------------------

        base_url = "https://api.football-data.org/v4/matches"
        headers = {
            'X-Auth-Token': API_TOKEN
        }

        # Calculamos rango: Desde Ayer hasta Mañana
        hoy = timezone.now().date()
        ayer = hoy - timedelta(days=1)
        manana = hoy + timedelta(days=1)

        # En esta API podemos pedir todo junto en una sola llamada
        params = {
            'dateFrom': ayer.strftime('%Y-%m-%d'),
            'dateTo': manana.strftime('%Y-%m-%d')
        }

        try:
            response = requests.get(base_url, headers=headers, params=params)
            data = response.json()

            # Diagnóstico de errores
            if 'errorCode' in data:
                self.stdout.write(self.style.WARNING(f"⚠️ Error API: {data.get('message')}"))
                return

            partidos_api = data.get('matches', [])
            self.stdout.write(f"✅ Conexión exitosa. Encontrados: {len(partidos_api)} partidos en el rango.")

            count_actualizados = 0

            for item in partidos_api:
                # 1. Datos API (La estructura cambia en esta API)
                nombre_local_api = item['homeTeam']['name']
                nombre_visitante_api = item['awayTeam']['name']
                
                # MODO ESPÍA ACTIVADO
                estado = item['status'] # SCHEDULED, TIMED, FINISHED, IN_PLAY
                self.stdout.write(f"👀 API ve: {nombre_local_api} vs {nombre_visitante_api} ({estado})")

                # Goles (FullTime)
                goles_local = item['score']['fullTime']['home']
                goles_visitante = item['score']['fullTime']['away']
                
                # Logos (Crest)
                logo_local = item['homeTeam'].get('crest')
                logo_visitante = item['awayTeam'].get('crest')

                # 2. Buscar en DB
                # Nota: Esta API usa nombres en inglés (Spain vs Brazil)
                partido_db = Match.objects.filter(
                    home_team__name__icontains=nombre_local_api,
                    away_team__name__icontains=nombre_visitante_api
                ).first()

                if partido_db:
                    cambios = False

                    # A. Actualizar Goles (Solo si el partido terminó o está en juego)
                    if goles_local is not None and goles_visitante is not None:
                        if partido_db.home_goals != goles_local or partido_db.away_goals != goles_visitante:
                            partido_db.home_goals = goles_local
                            partido_db.away_goals = goles_visitante
                            cambios = True

                    # B. Actualizar Logos
                    if logo_local and partido_db.home_team.logo != logo_local:
                        partido_db.home_team.logo = logo_local
                        partido_db.home_team.save()
                        self.stdout.write(f"      🛡️ Logo actualizado: {nombre_local_api}")

                    if logo_visitante and partido_db.away_team.logo != logo_visitante:
                        partido_db.away_team.logo = logo_visitante
                        partido_db.away_team.save()
                        self.stdout.write(f"      🛡️ Logo actualizado: {nombre_visitante_api}")

                    # Guardar cambios
                    if cambios:
                        partido_db.save()
                        self.stdout.write(self.style.SUCCESS(f"      ✅ Goles actualizados: {nombre_local_api} {goles_local}-{goles_visitante}"))
                        count_actualizados += 1
            
            if count_actualizados == 0:
                self.stdout.write("ℹ️ No se actualizaron partidos (probablemente por diferencias de nombres).")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error crítico: {e}"))