from django.core.management.base import BaseCommand
from core.models import Match
import requests
from django.utils import timezone
from datetime import timedelta # <--- Importante para calcular "ayer" y "mañana"

class Command(BaseCommand):
    help = 'Actualiza partidos de Ayer, Hoy y Mañana'

    def handle(self, *args, **kwargs):
        self.stdout.write("📡 Iniciando actualización masiva...")

        # TU CONFIGURACIÓN
        base_url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            'x-apisports-key': '8bfe23f584f1867b8ac0841f70d12009' 
        }

        # --- LÓGICA DE FECHAS DINÁMICAS ---
        # Calculamos las fechas: Ayer, Hoy, Mañana
        hoy = timezone.now().date()
        fechas_a_revisar = [
            hoy - timedelta(days=1), # Ayer (para resultados finales)
            hoy,                     # Hoy (para partidos en vivo)
            hoy + timedelta(days=1)  # Mañana (para traer logos de partidos nuevos)
        ]

        # BUCLE PRINCIPAL: Repetimos el proceso por cada fecha
        for fecha in fechas_a_revisar:
            fecha_str = fecha.strftime('%Y-%m-%d')
            self.stdout.write(f"📅 Consultando fecha: {fecha_str}...")

            params = {
                'date': fecha_str
            }

            try:
                response = requests.get(base_url, headers=headers, params=params)
                
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"❌ Error API en {fecha_str}"))
                    continue # Salta a la siguiente fecha

                data = response.json()
                # --- NUEVO: DIAGNÓSTICO DE ERRORES ---
                # Verificamos si la API nos está gritando un error silencioso
                errores = data.get('errors')
                if errores:
                # Si hay errores (ej: cuota excedida, plan bloqueado), los imprimimos
                # A veces 'errors' es una lista y a veces un diccionario, esto lo maneja:
                self.stdout.write(self.style.WARNING(f"⚠️ ALERTA API en {fecha_str}: {errores}"))
                continue # Saltamos al siguiente día
                # -------------------------------------

                partidos_api = data.get('response', [])
                
                self.stdout.write(f"   --> Encontrados en API: {len(partidos_api)} partidos")

                count_actualizados = 0

                for item in partidos_api:
                    # 1. Datos API
                    nombre_local_api = item['teams']['home']['name']
                    nombre_visitante_api = item['teams']['away']['name']
                    goles_local = item['goals']['home']
                    goles_visitante = item['goals']['away']
                    estado = item['fixture']['status']['short']
                    
                    # Logos
                    logo_local = item['teams']['home']['logo']
                    logo_visitante = item['teams']['away']['logo']

                    # 2. Buscar en DB
                    partido_db = Match.objects.filter(
                        home_team__name__icontains=nombre_local_api,
                        away_team__name__icontains=nombre_visitante_api
                    ).first()

                    if partido_db:
                        cambios = False

                        # A. Actualizar Goles (Solo si hay datos nuevos)
                        if goles_local is not None and goles_visitante is not None:
                            if partido_db.home_goals != goles_local or partido_db.away_goals != goles_visitante:
                                partido_db.home_goals = goles_local
                                partido_db.away_goals = goles_visitante
                                cambios = True

                        # B. Actualizar Logos (Si faltan o cambiaron)
                        if partido_db.home_team.logo != logo_local:
                            partido_db.home_team.logo = logo_local
                            partido_db.home_team.save()
                            self.stdout.write(f"      🛡️ Logo actualizado: {nombre_local_api}")

                        if partido_db.away_team.logo != logo_visitante:
                            partido_db.away_team.logo = logo_visitante
                            partido_db.away_team.save()
                            self.stdout.write(f"      🛡️ Logo actualizado: {nombre_visitante_api}")

                        # Guardar cambios del partido
                        if cambios:
                            partido_db.save()
                            self.stdout.write(self.style.SUCCESS(f"      ✅ Goles actualizados: {nombre_local_api} {goles_local}-{goles_visitante} {nombre_visitante_api}"))
                            count_actualizados += 1
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error crítico en {fecha_str}: {e}"))

        self.stdout.write(self.style.SUCCESS("✨ Proceso finalizado."))