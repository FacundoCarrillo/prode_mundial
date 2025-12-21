from django.core.management.base import BaseCommand
from core.models import Match, Competition, Team
import requests
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Actualiza partidos respetando la Competición y la Ronda'

    def handle(self, *args, **kwargs):
        self.stdout.write("📡 Conectando a Football-Data.org...")

        # --- TU TOKEN (Tomado de tu archivo original) ---
        API_TOKEN = '1988cfde850245faaaceaf5d9ff33ada' 
        headers = {'X-Auth-Token': API_TOKEN}
        base_url = "https://api.football-data.org/v4/competitions"

        # 1. Iteramos solo sobre las competiciones que cargaste en la DB
        competiciones_activas = Competition.objects.all()

        if not competiciones_activas:
            self.stdout.write(self.style.ERROR("❌ No hay competiciones cargadas en la base de datos. Creálas en el Admin primero."))
            return

        for comp in competiciones_activas:
            self.stdout.write(f"\n🏆 Procesando: {comp.name} (ID API: {comp.api_id})...")
            
            # Pedimos los partidos de ESTA competición
            # Traemos partidos recientes y futuros cercanos (Rango amplio para fixture)
            hoy = timezone.now().date()
            desde = hoy - timedelta(days=5) 
            hasta = hoy + timedelta(days=15)
            
            url = f"{base_url}/{comp.api_id}/matches"
            params = {
                'dateFrom': desde.strftime('%Y-%m-%d'),
                'dateTo': hasta.strftime('%Y-%m-%d')
            }

            try:
                response = requests.get(url, headers=headers, params=params)
                data = response.json()

                if 'errorCode' in data:
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Error API: {data.get('message')}"))
                    continue

                partidos_api = data.get('matches', [])
                self.stdout.write(f"   ✅ Encontrados: {len(partidos_api)} partidos.")

                for item in partidos_api:
                    # --- A. PROCESAR EQUIPOS ---
                    # Usamos get_or_create para no duplicar
                    local, _ = Team.objects.get_or_create(
                        name=item['homeTeam']['name'],
                        defaults={
                            'logo': item['homeTeam'].get('crest'),
                            'flag_code': item['homeTeam'].get('tla', 'XX')
                        }
                    )
                    visitante, _ = Team.objects.get_or_create(
                        name=item['awayTeam']['name'],
                        defaults={
                            'logo': item['awayTeam'].get('crest'),
                            'flag_code': item['awayTeam'].get('tla', 'XX')
                        }
                    )

                    # --- B. DETECTAR RONDA (Vital para tu lista plegable) ---
                    # La API devuelve 'matchday' (ej: 10) o 'stage' (ej: GROUP_STAGE)
                    ronda = item.get('matchday')
                    stage = item.get('stage')
                    
                    if ronda:
                        nombre_ronda = f"Fecha {ronda}"
                    else:
                        # Limpiamos el nombre feo de la API (Ej: REGULAR_SEASON -> Regular Season)
                        nombre_ronda = stage.replace('_', ' ').title() if stage else "General"

                    # --- C. DATOS DEL PARTIDO ---
                    fecha_str = item['utcDate']
                    estado = item['status']
                    goles_local = item['score']['fullTime']['home']
                    goles_visitante = item['score']['fullTime']['away']

                    # --- D. BUSCAR O CREAR PARTIDO ---
                    # Ahora filtramos TAMBIÉN por competición para evitar cruces
                    match_obj, created = Match.objects.get_or_create(
                        competition=comp,
                        home_team=local,
                        away_team=visitante,
                        defaults={
                            'date': fecha_str,
                            'status': estado,
                            'round_name': nombre_ronda, # <--- Guardamos la ronda aquí
                            'home_goals': goles_local,
                            'away_goals': goles_visitante
                        }
                    )

                    if not created:
                        # Si ya existe, actualizamos datos clave
                        cambios = False
                        if match_obj.status != estado:
                            match_obj.status = estado
                            cambios = True
                        if match_obj.home_goals != goles_local:
                            match_obj.home_goals = goles_local
                            match_obj.away_goals = goles_visitante
                            cambios = True
                        if match_obj.date != item['utcDate']: # Por si cambió el horario
                            # Ojo: comparar strings de fecha puede ser truculento, pero sirve para cambios grandes
                            pass 
                        
                        if cambios:
                            match_obj.save()
                            self.stdout.write(f"      🔄 Actualizado: {local} vs {visitante}")
                    else:
                        self.stdout.write(self.style.SUCCESS(f"      ✨ Nuevo: {local} vs {visitante} ({nombre_ronda})"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error conectando: {e}"))

        self.stdout.write(self.style.SUCCESS("\n✅ Proceso de carga finalizado."))